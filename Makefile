.PHONY: all clean superclean validate
.DEFAULT_GOAL := all

all: inferred.ttl diff.txt vocab.png description.png

clean:
	rm -f inferred.ttl diff.txt *.png

superclean: clean
	$(MAKE) -s -C tools/jena clean
	$(MAKE) -s -C tools/rdflib clean

tools/jena/bin/riot:
	$(MAKE) -s -C tools/jena

tools/rdflib/bin/rdf2dot:
	$(MAKE) -s -C tools/rdflib

validate: vocab.ttl description.ttl | tools/jena/bin/riot
	./tools/jena/bin/riot --validate $^
	@echo "vocab.ttl and description.ttl are valid."

inferred.ttl: vocab.ttl description.ttl | validate
	./tools/jena/bin/riot --formatted=ttl --rdfs $< $(word 2,$^) > $@

diff.txt: description.ttl inferred.ttl | validate
	./tools/jena/bin/riot --validate inferred.ttl
	@echo "inferred.ttl is valid."
	@./tools/jena/bin/rdfdiff $^ TTL TTL > $@ ; \
	[ $$? -eq 0 ] \
	&& (echo "\033[1;31mNo triples were inferred!\033[0m" ; rm -f $@) \
	|| echo "Triples were inferred!"

%.png: %.ttl | validate tools/rdflib/bin/rdf2dot
	./tools/rdflib/bin/rdf2dot $< | dot -Tpng > $@
