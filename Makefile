install:
	pip install -r requirements.txt
	curl --proto '=https' --tlsv1.2 -fsSL https://get.opentofu.org/install-opentofu.sh | bash -s -- --install-method standalone

.PHONY: install
