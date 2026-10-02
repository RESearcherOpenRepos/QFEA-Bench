ARG BASE_IMAGE=benchmark-base:tangelo_387_390
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=tangelo_387_390
ENV REPOSITORY=sandbox-quantum/Tangelo
ENV REPOSITORY_URL=https://github.com/sandbox-quantum/Tangelo.git
ENV ISSUE_URL=https://github.com/sandbox-quantum/Tangelo/issues/387
ENV PR_URL=https://github.com/sandbox-quantum/Tangelo/pull/390
ENV BASE_COMMIT=7ae4afd67f281e2b3dffb5f4ed616074ef38e387
ENV PATCHED_COMMIT=651c28ec97ed2da097254e39f171191870105799
ENV PR_HEAD_COMMIT=f153aa6dc03c16ff4042570259886a46877f1685
ENV FAIL_PASS_TEST_PATHS="tangelo/linq/tests/test_translator_circuit.py::TranslateCircuitTest::test_qiskit_multi_control"
ENV PASS_PASS_TEST_PATHS="tangelo/linq/tests/test_translator_circuit.py::TranslateCircuitTest::test_qiskit tangelo/linq/tests/test_translator_circuit.py::TranslateCircuitTest::test_openqasm2abs tangelo/linq/tests/test_translator_circuit.py::TranslateCircuitTest::test_unsupported_gate"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
