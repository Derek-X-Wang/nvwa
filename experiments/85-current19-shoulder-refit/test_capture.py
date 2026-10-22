"""Actual short-lived subprocess lifecycle controls. No Nvwa capture/geometry."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from capture import consume_process
from test_current19 import rows,encoded,RUN


class ProducerDeadlineControls(unittest.TestCase):
    def stopped(self,result):
        self.assertIsNotNone(result['producer_exit_code'])
        self.assertTrue(result['reader_exited'])
        with self.assertRaises(ProcessLookupError):os.kill(result['producer_pid'],0)

    def test_actual_hanging_stdout_terminated(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)
            result=consume_process([sys.executable,'-B','-c','import time; time.sleep(30)'],
                                   os.environ.copy(),out,out,RUN,timeout_seconds=.15)
            self.assertIn('deadline',result['failure'])
            self.assertLess(result['elapsed_seconds'],4)
            self.stopped(result)

    def test_actual_complete_stdout_but_process_hangs(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);out=root/'output';out.mkdir()
            data=root/'synthetic-stream.txt';data.write_text(''.join(encoded(rows())))
            command=[sys.executable,'-B','-c',
                     'import sys,os,time; sys.stdout.write(open(sys.argv[1]).read()); '
                     'sys.stdout.flush(); os.close(1); time.sleep(30)',str(data)]
            result=consume_process(command,os.environ.copy(),root,out,RUN,timeout_seconds=2)
            self.assertIsNotNone(result['failure'])
            self.assertEqual(len(result['entries']),19)
            self.assertEqual(len(list((out/'raw').glob('*.json'))),20)
            self.assertLess(result['elapsed_seconds'],5)
            self.stopped(result)

    def test_actual_complete_producer_exits_successfully(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);out=root/'output';out.mkdir()
            data=root/'synthetic-stream.txt';data.write_text(''.join(encoded(rows())))
            command=[sys.executable,'-B','-c','import sys; sys.stdout.write(open(sys.argv[1]).read())',str(data)]
            result=consume_process(command,os.environ.copy(),root,out,RUN,timeout_seconds=3)
            self.assertIsNone(result['failure'])
            self.assertEqual(result['producer_exit_code'],0)
            self.assertEqual(len(result['entries']),19)
            self.stopped(result)


if __name__=='__main__':unittest.main()
