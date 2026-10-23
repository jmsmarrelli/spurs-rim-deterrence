# Pipeline stages share generated inputs and must run in order.
.NOTPARALLEL:
PY ?= python3

.PHONY: all build deterrence offense clean site

all: verify-data build deterrence offense

build:
	$(PY) src/run_01_build.py

deterrence:
	$(PY) src/run_02_deterrence.py

offense:
	$(PY) src/run_03_offense.py

# Regenerate the GitHub Pages page from README.md. Needs `pip install -r requirements.txt`.
site:
	$(PY) tools/site.py

clean:
	rm -f figures/*.png output/*.csv output/*.log data/processed/*

.PHONY: fetch-data verify-data
fetch-data:
	$(PY) tools/fetch_data.py

verify-data:
	$(PY) tools/fetch_data.py --check

.PHONY: report
report:
	$(PY) tools/report.py
