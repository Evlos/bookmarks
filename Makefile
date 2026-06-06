default:
	flask --app app run --host=0.0.0.0 --port=30808

repomix:
	repomix --include "*.py" -o telegram_next.xml
