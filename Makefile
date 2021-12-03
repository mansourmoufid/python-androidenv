.PHONY: sdist
sdist:
	python setup.py sdist --formats=gztar

.PHONY: cleanup
cleanup:
	rm -rf build

.PHONY: clean
clean: cleanup
	rm -rf dist
