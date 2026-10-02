ARG BASE_IMAGE=benchmark-base:tangelo_384_398
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=tangelo_384_398
ENV REPOSITORY=sandbox-quantum/Tangelo
ENV REPOSITORY_URL=https://github.com/sandbox-quantum/Tangelo.git
ENV ISSUE_URL=https://github.com/sandbox-quantum/Tangelo/issues/384
ENV PR_URL=https://github.com/sandbox-quantum/Tangelo/pull/398
ENV BASE_COMMIT=c8c9ac1d562b1ae352236a1994803e7ee16ce57f
ENV PATCHED_COMMIT=9e286675b2d2d33d0cf0da0ee7cf910a41143eb8
ENV PR_HEAD_COMMIT=033e3026e0bd1f7d3268e45c1e69849eddb7cee0
ENV FAIL_PASS_TEST_PATHS="tangelo/toolboxes/ansatz_generator/tests/test_hea.py::HEATest::test_hea_circuit_variational_reference_state tangelo/toolboxes/ansatz_generator/tests/test_hea.py::HEATest::test_hea_circuit_reference_state_H2"
ENV PASS_PASS_TEST_PATHS="tangelo/toolboxes/ansatz_generator/tests/test_hea.py::HEATest::test_hea_set_var_params tangelo/toolboxes/ansatz_generator/tests/test_hea.py::HEATest::test_hea_incorrect_number_var_params tangelo/toolboxes/ansatz_generator/tests/test_hea.py::HEATest::test_hea_H2"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
