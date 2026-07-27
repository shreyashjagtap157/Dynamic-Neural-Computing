@echo off
python -c "import sys; sys.path.insert(0,'src'); exec(open('tests/conformance/test_decision_policy.py').read())" > _r1.txt 2>&1
python -c "import sys; sys.path.insert(0,'src'); exec(open('tests/conformance/test_replay_semantics.py').read())" > _r2.txt 2>&1
python -c "import sys; sys.path.insert(0,'src'); exec(open('tests/conformance/test_evaluation.py').read())" > _r3.txt 2>&1
python -c "import sys; sys.path.insert(0,'src'); exec(open('tests/conformance/test_execution_invariants.py').read())" > _r4.txt 2>&1
python -c "import sys; sys.path.insert(0,'src'); exec(open('tests/conformance/scheduler/test_scheduler_invariants.py').read())" > _r5.txt 2>&1
echo DONE
