ARG BASE_IMAGE=benchmark-base:openfermion_457_549
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=openfermion_457_549
ENV REPOSITORY=quantumlib/OpenFermion
ENV REPOSITORY_URL=https://github.com/quantumlib/OpenFermion.git
ENV ISSUE_URL=https://github.com/quantumlib/OpenFermion/issues/457
ENV PR_URL=https://github.com/quantumlib/OpenFermion/pull/549
ENV BASE_COMMIT=427e5c53b1008e3aee16ecc277bb8094169a3310
ENV PATCHED_COMMIT=302449a45ef0106a1ac210174ddefc2b7ffb71a6
ENV PR_HEAD_COMMIT=302449a45ef0106a1ac210174ddefc2b7ffb71a6
ENV FAIL_PASS_TEST_PATHS="src/openfermion/ops/_symbolic_operator_test.py::SymbolicOperatorTest1::test_init_with_sympy src/openfermion/ops/_symbolic_operator_test.py::SymbolicOperatorTest1::test_imul_sympy src/openfermion/ops/_symbolic_operator_test.py::SymbolicOperatorTest1::test_iadd_sympy_term_removal src/openfermion/transforms/_jordan_wigner_test.py::JordanWignerTransformTest::test_transm_raise3_sympy src/openfermion/transforms/_bravyi_kitaev_test.py::BravyiKitaevTransformTest::test_bravyi_kitaev_transform_sympy"
ENV PASS_PASS_TEST_PATHS="src/openfermion/ops/_symbolic_operator_test.py::SymbolicOperatorTest1::test_init_tuple_complex_coefficient src/openfermion/ops/_symbolic_operator_test.py::SymbolicOperatorTest1::test_imul_scalar_complex src/openfermion/ops/_symbolic_operator_test.py::SymbolicOperatorTest1::test_iadd_different_term src/openfermion/transforms/_jordan_wigner_test.py::JordanWignerTransformTest::test_transm_raise3 src/openfermion/transforms/_bravyi_kitaev_test.py::BravyiKitaevTransformTest::test_bravyi_kitaev_transform"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
