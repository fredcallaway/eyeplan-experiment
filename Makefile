run:
	git pull
	sh get_consent
	python main.py
	open forms/debrief.pdf

fetch:
	rsync -av ~/drive/eyeplan-data/ data/
	rsync -av ~/drive/eyeplan-log/ log/
