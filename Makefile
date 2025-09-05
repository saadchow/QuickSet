.PHONY: run refresh pwi

run:
	uvicorn app.main:app --reload

refresh:
	python -m app.refresh

pwi:
	python -m playwright install chromium
