FROM benchmark-base:pennylane_5895_5920

ENV SAMPLE_ID=pennylane_5895_5920
ENV REPOSITORY_URL=https://github.com/PennyLaneAI/pennylane.git
ENV BASE_COMMIT=497721a3bb0a2defa07c6ac1f9de8a56cb73bb55
ENV PATCHED_COMMIT=0dacfd48cc696be2733a499bcb08b496f4050c3c
ENV FAIL_PASS_TEST_PATHS="tests/fermi/test_fermionic.py::TestFermiWord::test_to_mat tests/fermi/test_fermionic.py::TestFermiSentence::test_to_mat"
ENV PASS_PASS_TEST_PATHS="tests/fermi/test_fermionic.py::TestFermiWord::test_missing tests/fermi/test_fermionic.py::TestFermiWord::test_pickling tests/fermi/test_fermionic.py::TestFermiSentence::test_simplify tests/fermi/test_fermionic.py::TestFermiSentence::test_pickling"

WORKDIR /benchmark
COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
