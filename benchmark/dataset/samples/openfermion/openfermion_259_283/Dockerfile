ARG BASE_IMAGE=benchmark-base:openfermion_259_283
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=openfermion_259_283
ENV REPOSITORY=quantumlib/OpenFermion
ENV REPOSITORY_URL=https://github.com/quantumlib/OpenFermion.git
ENV ISSUE_URL=https://github.com/quantumlib/OpenFermion/issues/259
ENV PR_URL=https://github.com/quantumlib/OpenFermion/pull/283
ENV BASE_COMMIT=5c2c44b09878eda626a7838ae5fc7b7e2a86f2b6
ENV PATCHED_COMMIT=889bc9c2a70b877014261d76237a4b88de63e66e
ENV PR_HEAD_COMMIT=889bc9c2a70b877014261d76237a4b88de63e66e
ENV FAIL_PASS_TEST_PATHS="src/openfermion/transforms/_bravyi_kitaev_tree_test.py::BravyiKitaevTransformTest::test_bravyi_kitaev_tree_transform src/openfermion/transforms/_bravyi_kitaev_tree_test.py::BravyiKitaevTransformTest::test_bk_identity src/openfermion/transforms/_bravyi_kitaev_tree_test.py::BravyiKitaevTransformTest::test_bk_n_qubits_too_small src/openfermion/transforms/_bravyi_kitaev_tree_test.py::BravyiKitaevTransformTest::test_bk_jw_number_operator"
ENV PASS_PASS_TEST_PATHS="src/openfermion/transforms/_bravyi_kitaev_test.py::BravyiKitaevTransformTest::test_bravyi_kitaev_transform src/openfermion/transforms/_bravyi_kitaev_test.py::BravyiKitaevTransformTest::test_bk_identity src/openfermion/transforms/_bravyi_kitaev_test.py::BravyiKitaevTransformTest::test_bk_n_qubits_too_small src/openfermion/transforms/_bravyi_kitaev_test.py::BravyiKitaevTransformTest::test_bk_jw_number_operator"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
