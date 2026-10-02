ARG BASE_IMAGE=benchmark-base:openfermion_37_114
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=openfermion_37_114
ENV REPOSITORY=quantumlib/OpenFermion
ENV REPOSITORY_URL=https://github.com/quantumlib/OpenFermion.git
ENV ISSUE_URL=https://github.com/quantumlib/OpenFermion/issues/37
ENV PR_URL=https://github.com/quantumlib/OpenFermion/pull/114
ENV BASE_COMMIT=b42cc79c5da70e51fef54e9d87ac6004458f8396
ENV PATCHED_COMMIT=5491510d216f5f2cab751084194f4c233d04167e
ENV PR_HEAD_COMMIT=5491510d216f5f2cab751084194f4c233d04167e
ENV FAIL_PASS_TEST_PATHS="src/openfermion/utils/_bch_expansion_test.py::BCHTest::test_bch src/openfermion/utils/_bch_expansion_test.py::BCHTest::test_verification"
ENV PASS_PASS_TEST_PATHS="src/openfermion/utils/_operator_utils_test.py::CommutatorTest::test_commutes_identity src/openfermion/utils/_operator_utils_test.py::CommutatorTest::test_commutes_no_intersection src/openfermion/utils/_operator_utils_test.py::CommutatorTest::test_commutator_hopping_operators src/openfermion/utils/_operator_utils_test.py::CommutatorTest::test_ndarray_input src/openfermion/utils/_operator_utils_test.py::CommutatorTest::test_commutator_not_same_type"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
