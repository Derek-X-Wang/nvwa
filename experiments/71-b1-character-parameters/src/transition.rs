//! Typed request readiness policy used by the actual observer, without renderer
//! dependencies. Standalone tests certify policy only, never production frames.
#[derive(Default)]
pub(crate) struct State<'a> {
    pub elapsed: f64,
    pub errors: [Option<&'a str>; 4],
    pub appearance_error: Option<&'a str>,
    pub playback_error: Option<&'a str>,
    pub preview: bool,
    pub pending_open: bool,
    pub runtime_ready: bool,
    pub appearance_ready: bool,
    pub appearance_pending: bool,
    pub seek_pending: bool,
}

#[derive(Debug, PartialEq, Eq)]
pub(crate) enum Readiness {
    Waiting,
    Ready,
}

pub(crate) fn check(state: State<'_>) -> Result<Readiness, String> {
    if state.elapsed > 45. {
        return Err(
            "request did not reach current stable production identity within45seconds".into(),
        );
    }
    let appearance_error = if state.appearance_pending {
        None
    } else {
        state.appearance_error
    };
    if let Some(error) = state
        .errors
        .into_iter()
        .chain([appearance_error, state.playback_error])
        .flatten()
        .next()
    {
        return Err(error.into());
    }
    if state.preview {
        return Err("cannot certify saved Work while an editor preview is active; commit or cancel the preview".into());
    }
    if state.pending_open
        || !state.runtime_ready
        || !state.appearance_ready
        || state.appearance_pending
        || state.seek_pending
    {
        Ok(Readiness::Waiting)
    } else {
        Ok(Readiness::Ready)
    }
}

pub(crate) fn reset_stability<T>(previous: &mut Option<T>, count: &mut u8) {
    *previous = None;
    *count = 0;
}

pub(crate) fn stable_observation<T: PartialEq + Clone>(
    previous: &mut Option<T>,
    count: &mut u8,
    current: &T,
) -> bool {
    if previous.as_ref() == Some(current) {
        *count = count.saturating_add(1).min(2);
    } else {
        *previous = Some(current.clone());
        *count = 1;
    }
    *count >= 2
}

#[cfg(test)]
mod tests {
    use super::*;
    fn ready() -> State<'static> {
        State {
            runtime_ready: true,
            appearance_ready: true,
            ..State::default()
        }
    }
    #[test]
    fn typed_pending_reason_waits_then_ready_requires_two_fresh_held_observations() {
        let mut previous = None;
        let mut count = 0;
        assert!(!stable_observation(&mut previous, &mut count, &"current"));
        let state = State {
            elapsed: 44.,
            appearance_pending: true,
            appearance_error: Some("opaque transition reason"),
            ..ready()
        };
        assert_eq!(check(state), Ok(Readiness::Waiting));
        reset_stability(&mut previous, &mut count);
        assert!(previous.is_none());
        assert_eq!(count, 0);
        assert_eq!(check(ready()), Ok(Readiness::Ready));
        assert!(!stable_observation(&mut previous, &mut count, &"current"));
        assert!(stable_observation(&mut previous, &mut count, &"current"));
    }
    #[test]
    fn every_real_error_propagates_even_during_typed_appearance_pending() {
        for index in 0..4 {
            let mut state = State {
                appearance_pending: true,
                appearance_error: Some("pending reason"),
                ..ready()
            };
            state.errors[index] = Some("retained actual failure");
            assert_eq!(check(state), Err("retained actual failure".into()));
        }
        assert_eq!(
            check(State {
                appearance_pending: true,
                playback_error: Some("actual playback failure"),
                ..ready()
            }),
            Err("actual playback failure".into())
        );
    }
    #[test]
    fn nonpending_appearance_error_is_terminal_without_interpreting_its_text() {
        for message in ["opaque transition reason", "unknown", ""] {
            assert_eq!(
                check(State {
                    appearance_error: Some(message),
                    ..ready()
                }),
                Err(message.into())
            );
        }
    }
    #[test]
    fn same_pending_reason_does_not_restart_or_bypass_original_deadline() {
        assert_eq!(
            check(State {
                elapsed: 45.,
                appearance_pending: true,
                ..ready()
            }),
            Ok(Readiness::Waiting)
        );
        assert_eq!(
            check(State {
                elapsed: 45.001,
                appearance_pending: true,
                appearance_error: Some("opaque transition reason"),
                ..ready()
            }),
            Err("request did not reach current stable production identity within45seconds".into())
        );
    }
    #[test]
    fn open_runtime_appearance_and_seek_transitions_all_wait() {
        let states = [
            State {
                pending_open: true,
                ..ready()
            },
            State {
                runtime_ready: false,
                ..ready()
            },
            State {
                appearance_ready: false,
                ..ready()
            },
            State {
                appearance_pending: true,
                ..ready()
            },
            State {
                seek_pending: true,
                ..ready()
            },
        ];
        for state in states {
            assert_eq!(check(state), Ok(Readiness::Waiting));
        }
    }
    #[test]
    fn preview_is_never_certified_even_during_pending() {
        assert!(
            check(State {
                preview: true,
                appearance_pending: true,
                ..ready()
            })
            .is_err()
        );
    }
    #[test]
    fn changed_identity_needs_two_new_observations() {
        let mut previous = None;
        let mut count = 0;
        assert!(!stable_observation(&mut previous, &mut count, &7));
        assert!(stable_observation(&mut previous, &mut count, &7));
        assert!(!stable_observation(&mut previous, &mut count, &8));
        assert!(stable_observation(&mut previous, &mut count, &8));
    }
}
