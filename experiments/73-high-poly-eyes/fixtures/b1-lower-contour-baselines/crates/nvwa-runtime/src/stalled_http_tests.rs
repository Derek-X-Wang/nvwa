//! Throwaway loopback HTTP adapter; exercises the production AssetServer loader.
//! No HTTP/network library or production transport policy is introduced here.
use super::*;
use std::{
    io::{Read, Write},
    net::{SocketAddr, TcpListener, TcpStream},
    sync::{Mutex, atomic::AtomicBool},
    thread::JoinHandle,
    time::{Duration, Instant},
};

type HttpResult = Result<Vec<u8>, std::io::Error>;
#[derive(Default)]
struct ReplyState {
    result: Option<HttpResult>,
    waker: Option<std::task::Waker>,
}
#[derive(Clone)]
struct HttpReader {
    address: SocketAddr,
    reads: Arc<AtomicUsize>,
    clients: Arc<Mutex<Vec<JoinHandle<()>>>>,
}
impl AssetReader for HttpReader {
    async fn read<'a>(&'a self, path: &'a Path) -> Result<impl Reader + 'a, AssetReaderError> {
        let read_id = self.reads.fetch_add(1, Ordering::SeqCst) + 1;
        let trace_dir =
            std::env::var_os("NVWA_STALLED_HTTP_TRACE_DIR").map(std::path::PathBuf::from);
        let reply = Arc::new(Mutex::new(ReplyState::default()));
        let output = reply.clone();
        let address = self.address;
        let path = path.display().to_string();
        let client = std::thread::spawn(move || {
            let result = (|| -> HttpResult {
                let mut stream = TcpStream::connect_timeout(&address, Duration::from_secs(2))?;
                stream.set_read_timeout(Some(Duration::from_secs(5)))?;
                stream.set_write_timeout(Some(Duration::from_secs(2)))?;
                stream.write_all(format!(
                    "GET /{path} HTTP/1.1\r\nHost: {address}\r\nX-Nvwa-Read: {read_id}\r\nConnection: close\r\n\r\n"
                ).as_bytes())?;
                let mut response = Vec::new();
                stream
                    .take((FIXTURE.len() + 4096) as u64)
                    .read_to_end(&mut response)?;
                let split = response
                    .windows(4)
                    .position(|v| v == b"\r\n\r\n")
                    .ok_or_else(|| std::io::Error::other("Missing HTTP response header"))?;
                if !response.starts_with(b"HTTP/1.1 200 ") {
                    return Err(std::io::Error::other("Loopback source returned failure"));
                }
                let header = std::str::from_utf8(&response[..split])
                    .map_err(|error| std::io::Error::other(error.to_string()))?;
                let expected = header
                    .lines()
                    .find_map(|line| line.strip_prefix("Content-Length: "))
                    .and_then(|value| value.trim().parse::<usize>().ok())
                    .ok_or_else(|| std::io::Error::other("Missing HTTP content length"))?;
                let body = &response[split + 4..];
                if let Some(dir) = &trace_dir {
                    std::fs::write(dir.join(format!("received-{read_id}.bin")), body)?;
                }
                eprintln!(
                    "HTTP_RECEIVED read={read_id} bytes={} expected={expected} exact_fixture={}",
                    body.len(),
                    body == FIXTURE
                );
                if body.len() != expected {
                    return Err(std::io::Error::other(format!(
                        "Incomplete HTTP body: expected {expected}, received {}",
                        body.len()
                    )));
                }
                Ok(body.to_vec())
            })();
            let mut state = output.lock().unwrap();
            state.result = Some(result);
            if let Some(waker) = state.waker.take() {
                waker.wake();
            }
        });
        self.clients.lock().unwrap().push(client);
        let bytes = std::future::poll_fn(|cx| {
            let mut state = reply.lock().unwrap();
            if let Some(result) = state.result.take() {
                std::task::Poll::Ready(result)
            } else {
                state.waker = Some(cx.waker().clone());
                std::task::Poll::Pending
            }
        })
        .await?;
        Ok(VecReader::new(bytes))
    }
    async fn read_meta<'a>(&'a self, path: &'a Path) -> Result<impl Reader + 'a, AssetReaderError> {
        Err::<VecReader, _>(AssetReaderError::NotFound(path.to_path_buf()))
    }
    async fn read_directory<'a>(
        &'a self,
        path: &'a Path,
    ) -> Result<Box<PathStream>, AssetReaderError> {
        Err(AssetReaderError::NotFound(path.to_path_buf()))
    }
    async fn is_directory<'a>(&'a self, _: &'a Path) -> Result<bool, AssetReaderError> {
        Ok(false)
    }
}

struct HttpFixture {
    reader: HttpReader,
    gates: Arc<ReadGates>,
    stopped: Arc<AtomicBool>,
    server: Option<JoinHandle<()>>,
    responses: Arc<Mutex<Vec<JoinHandle<()>>>>,
}
impl HttpFixture {
    fn new() -> Self {
        // OS-assigned loopback port; no public bind or reserved application port.
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        listener.set_nonblocking(true).unwrap();
        let gates = Arc::new(ReadGates::default());
        let stopped = Arc::new(AtomicBool::new(false));
        let responses = Arc::new(Mutex::new(Vec::new()));
        let mutation = std::env::var_os("NVWA_STALLED_HTTP_NONBLOCKING_MUTATION").is_some();
        let trace_dir =
            std::env::var_os("NVWA_STALLED_HTTP_TRACE_DIR").map(std::path::PathBuf::from);
        if let Some(dir) = &trace_dir {
            std::fs::create_dir_all(dir).unwrap();
            std::fs::write(dir.join("attempted-body.bin"), FIXTURE).unwrap();
        }
        let (server_gates, server_stopped, server_responses) =
            (gates.clone(), stopped.clone(), responses.clone());
        let server = std::thread::spawn(move || {
            let deadline = Instant::now() + Duration::from_secs(10);
            while !server_stopped.load(Ordering::SeqCst) && Instant::now() < deadline {
                match listener.accept() {
                    Ok((mut stream, _)) => {
                        let stopped = server_stopped.clone();
                        let gates = server_gates.clone();
                        let trace_dir = trace_dir.clone();
                        server_responses.lock().unwrap().push(std::thread::spawn(move || {
                            // Accepted sockets can inherit the nonblocking listener
                            // flag on macOS. Response workers use bounded blocking IO.
                            if !mutation { stream.set_nonblocking(false).unwrap(); }
                            stream.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
                            stream.set_write_timeout(Some(Duration::from_secs(2))).unwrap();
                            let mut request = Vec::new();
                            let deadline = Instant::now() + Duration::from_secs(2);
                            while !request.windows(4).any(|v| v == b"\r\n\r\n") {
                                let mut chunk = [0; 512];
                                match stream.read(&mut chunk) {
                                    Ok(0) => return,
                                    Ok(n) => request.extend_from_slice(&chunk[..n]),
                                    Err(error) if error.kind() == std::io::ErrorKind::WouldBlock && Instant::now() < deadline => std::thread::sleep(Duration::from_millis(1)),
                                    Err(_) => return,
                                }
                                if request.len() > 4096 || Instant::now() >= deadline { return; }
                            }
                            let read_id = std::str::from_utf8(&request).unwrap().lines()
                                .find_map(|line| line.strip_prefix("X-Nvwa-Read: "))
                                .unwrap().trim().parse::<usize>().unwrap();
                            let gate = gates.enter();
                            let deadline = Instant::now() + Duration::from_secs(5);
                            while !gate.released.load(Ordering::SeqCst)
                                && !stopped.load(Ordering::SeqCst) && Instant::now() < deadline {
                                std::thread::sleep(Duration::from_millis(1));
                            }
                            if gate.failed.load(Ordering::SeqCst) {
                                let _ = stream.write_all(b"HTTP/1.1 404 Missing\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
                            } else {
                                let _ = write!(stream, "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n", FIXTURE.len());
                                let mut written = 0;
                                let mut failure = None;
                                while written < FIXTURE.len() {
                                    match stream.write(&FIXTURE[written..]) {
                                        Ok(0) => { failure = Some(std::io::ErrorKind::WriteZero); break; }
                                        Ok(n) => written += n,
                                        Err(error) if error.kind() == std::io::ErrorKind::Interrupted => continue,
                                        Err(error) => { failure = Some(error.kind()); break; }
                                    }
                                }
                                if let Some(dir) = &trace_dir {
                                    std::fs::write(dir.join(format!("sent-{read_id}.bin")), &FIXTURE[..written]).unwrap();
                                }
                                eprintln!("HTTP_SENT read={read_id} attempted={} accepted={written} mutation={mutation} failure={failure:?}", FIXTURE.len());
                            }
                        }));
                    }
                    Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                        std::thread::sleep(Duration::from_millis(1));
                    }
                    Err(_) => break,
                }
            }
        });
        Self {
            reader: HttpReader {
                address,
                reads: Arc::new(AtomicUsize::new(0)),
                clients: Arc::new(Mutex::new(Vec::new())),
            },
            gates,
            stopped,
            server: Some(server),
            responses,
        }
    }
}
impl Drop for HttpFixture {
    fn drop(&mut self) {
        self.stopped.store(true, Ordering::SeqCst);
        for gate in self.gates.0.lock().unwrap().iter() {
            gate.release();
        }
        let mut panics = 0;
        if let Some(server) = self.server.take() {
            panics += usize::from(server.join().is_err());
        }
        let mut response_threads = 0;
        for response in self.responses.lock().unwrap().drain(..) {
            panics += usize::from(response.join().is_err());
            response_threads += 1;
        }
        let mut reader_threads = 0;
        for client in self.reader.clients.lock().unwrap().drain(..) {
            panics += usize::from(client.join().is_err());
            reader_threads += 1;
        }
        let held = self
            .gates
            .0
            .lock()
            .unwrap()
            .iter()
            .filter(|gate| !gate.released.load(Ordering::SeqCst))
            .count();
        eprintln!(
            "HTTP_CLEANUP server_joined=1 response_threads_joined={response_threads} reader_threads_joined={reader_threads} held_gates={held} panics={panics}"
        );
        if !std::thread::panicking() {
            assert_eq!((held, panics), (0, 0));
        }
    }
}

#[test]
fn loopback_http_stalled_distinct_paths_bound_admission_and_recover_latest() {
    let source = HttpFixture::new();
    let profile =
        CharacterProfile::from_json(include_str!("../../../assets/character.profile.json"))
            .unwrap();
    let mut test = Harness::with_reader(
        profile,
        Dir::default(),
        source.reader.reads.clone(),
        source.reader.clone(),
    );
    test.until(|_| source.gates.entered() == 1);
    for index in 1..12 {
        let mut profile = test.profile.clone();
        profile.asset_path = format!("fixtures/http-stalled-{index}.glb");
        test.open(profile);
        drive_for(&mut test, Duration::from_millis(25));
    }
    let asset = test.app.world().resource::<CharacterAsset>();
    let retained = asset.retiring.len() + usize::from(asset.bytes.is_some());
    let server = test.app.world().resource::<AssetServer>();
    let loading_roots = asset
        .retiring
        .iter()
        .map(|load| load.id)
        .chain(asset.bytes.iter().map(Handle::id))
        .filter(|id| matches!(server.get_load_state(*id), Some(LoadState::Loading)))
        .count();
    let roots = test.app.world().resource::<Assets<CharacterGlb>>().len();
    let dependencies = test.app.world().resource::<Assets<Gltf>>().len();
    eprintln!(
        "HTTP_STALLED attempted=12 retained={retained} loading_roots={loading_roots} held_responses={} source_reads={} loaded_roots={roots} loaded_gltf_dependencies={dependencies}",
        source.gates.entered(),
        test.reads()
    );
    assert_eq!(retained, 4);
    assert_eq!(loading_roots, 4);
    assert_eq!(source.gates.entered(), 4);
    assert_eq!(test.reads(), 4);
    assert_eq!((roots, dependencies), (0, 0));
    assert!(asset.pending_open);
    source.gates.release(0);
    test.until(|_| source.gates.entered() == 5);
    assert_eq!(
        test.app.world().resource::<CharacterAsset>().path,
        "fixtures/http-stalled-11.glb"
    );
    source.gates.release(4);
    test.ready();
    let accepted = fingerprint(&mut test.app);
    for index in 1..4 {
        source.gates.release(index);
    }
    test.until(|world| world.resource::<CharacterAsset>().retiring.is_empty());
    assert_eq!(fingerprint(&mut test.app), accepted);
    assert_eq!(test.reads(), 5);
    eprintln!(
        "HTTP_RECOVERY reads={} retiring=0 ready=true loaded_roots={} loaded_gltf_dependencies={}",
        test.reads(),
        test.app.world().resource::<Assets<CharacterGlb>>().len(),
        test.app.world().resource::<Assets<Gltf>>().len()
    );
    // App drops before source: all test socket workers are joined by the fixture.
}
