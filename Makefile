JAVA ?= java
MAVEN ?= mvn

.PHONY: lint install clean package
install:
	./install.sh

package:
	$(MAVEN) package -DskipTests

lint:
	$(MAVEN) compile -q

clean:
	$(MAVEN) clean
	rm -rf target .venv build dist *.egg-info __pycache__ .myai-tasks.json .myai-update.lock
