run:
	git pull
	sh get_consent
	python main.py
	open forms/debrief.pdf