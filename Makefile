.PHONY: check
check:
	pycodestyle *.py
	pyflakes *.py

.PHONY: sdist
sdist:
	python setup.py sdist --formats=gztar

.PHONY: upload
upload:
	twine upload dist/* --verbose

.PHONY: cleanup
cleanup:
	rm -rf build

.PHONY: clean
clean: cleanup
	rm -rf dist
