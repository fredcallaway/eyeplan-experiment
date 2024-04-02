run:
	git pull
	sh get_consent
	python main.py
	open forms/debrief.pdf

test:
	git pull
	python main.py --test

fetch:
	rsync -av mattar-mini:/Users/labadmin/eyeplan-experiment/data/ data/
	rsync -av mattar-mini:/Users/labadmin/eyeplan-experiment/log/ log/