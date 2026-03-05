PORT := 8081

.PHONY: serve stop restart crawl install test clean

serve: stop
	python web_server.py

stop:
	-lsof -ti:$(PORT) | xargs kill 2>/dev/null || true

restart: stop serve

crawl:
	python main.py multi-crawl --all

install:
	pip install -r requirements.txt

test:
	python -m pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f data/*.tmp
