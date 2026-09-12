"""Zrušenie behu musí zabiť aj procesy, ktoré si beh sám spustil."""

from __future__ import annotations

import subprocess
import sys
import time

import pytest

psutil = pytest.importorskip("psutil")

from tester.webapp.runner import kill_tree

#: Rodič, ktorý spustí dieťa a čaká — presne ako hyperopt so svojimi workermi.
RODIC = (
    "import subprocess, sys, time\n"
    "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
    "time.sleep(120)\n"
)


def test_zabije_rodica_aj_deti():
    rodic = subprocess.Popen([sys.executable, "-c", RODIC])
    try:
        for _ in range(50):                        # pockat, kym dieta naozaj vznikne
            deti = psutil.Process(rodic.pid).children(recursive=True)
            if deti:
                break
            time.sleep(0.1)
        assert deti, "dieťa nevzniklo"
        dieta_pid = deti[0].pid

        assert kill_tree(rodic.pid) >= 2
        rodic.wait(timeout=10)
        assert not psutil.pid_exists(dieta_pid) or \
            psutil.Process(dieta_pid).status() == psutil.STATUS_ZOMBIE
    finally:
        if rodic.poll() is None:
            rodic.kill()


def test_neexistujuci_proces_nepadne():
    assert kill_tree(999999999) == 0
