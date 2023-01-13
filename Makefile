# For OS-independence, if needed
ifeq ($(OS), Windows_NT)
	TGT := win
	AND := ;
	PYTHON ?= python
else
	TGT := lin
	AND := ;
	PYTHON ?= python
endif


CD_TESTS := cd tests $(AND)
UNITTEST_CMD := -m unittest discover -p '*_test.py' -v


# ==== [ Targets ] ====
all: run

run: check-py-version
	$(PYTHON) ./run.py

test: check-py-version
	$(CD_TESTS) \
	$(PYTHON) $(UNITTEST_CMD)

testcov: check-py-version
	$(CD_TESTS) \
	$(PYTHON) -m coverage run $(UNITTEST_CMD) $(AND) \
	$(PYTHON) -m coverage report

check-py-version:
	@$(PYTHON) -c "import sys; min_version = (3, 9); v_repr = lambda v: '.'.join(map(str, v)); assert sys.version_info >= min_version, f\"Python version insufficient: {v_repr(min_version)}+ required, {v_repr(sys.version_info)} provided\""

.PHONY: all run test testcov
# =====================


