ARG BASE_IMAGE=benchmark-base:openfermion_46_61
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=openfermion_46_61
ENV REPOSITORY=quantumlib/OpenFermion
ENV REPOSITORY_URL=https://github.com/quantumlib/OpenFermion.git
ENV ISSUE_URL=https://github.com/quantumlib/OpenFermion/issues/46
ENV PR_URL=https://github.com/quantumlib/OpenFermion/pull/61
ENV BASE_COMMIT=03ce7e4c8f1c948b3b1834d48900166f5bc2ec41
ENV PATCHED_COMMIT=2945f996a6c0a49324590f8bbe959f4bd6a4b80c
ENV PR_HEAD_COMMIT=2945f996a6c0a49324590f8bbe959f4bd6a4b80c
ENV FAIL_PASS_TEST_PATHS="src/openfermion/ops/_polynomial_tensor_test.py::PolynomialTensorTest::test_invalid_tensor_keys_add src/openfermion/ops/_polynomial_tensor_test.py::PolynomialTensorTest::test_invalid_tensor_keys_sub src/openfermion/ops/_polynomial_tensor_test.py::PolynomialTensorTest::test_invalid_tensor_keys_mult src/openfermion/ops/_polynomial_tensor_test.py::PolynomialTensorTest::test_rotate_basis_identical"
ENV PASS_PASS_TEST_PATHS="src/openfermion/ops/_interaction_operator_test.py::InteractionOperatorsTest::test_four_point_iter src/openfermion/ops/_interaction_operator_test.py::InteractionOperatorsTest::test_eight_point_iter"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
