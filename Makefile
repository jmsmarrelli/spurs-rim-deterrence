PY := python3

.PHONY: all build deterrence offense clean site

all: build deterrence offense

build:
	$(PY) src/run_01_build.py

deterrence:
	$(PY) src/run_02_deterrence.py

offense:
	$(PY) src/run_03_offense.py

# Regenerate the GitHub Pages page from README.md. Needs `pip install markdown`.
site:
	$(PY) tools/site.py

clean:
	rm -f figures/*.png output/*.csv output/*.log data/processed/*
