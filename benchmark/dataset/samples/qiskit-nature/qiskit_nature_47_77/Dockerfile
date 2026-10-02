ARG BASE_IMAGE=benchmark-base:qiskit_nature_47_77
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_47_77
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/47
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/77
ENV BASE_COMMIT=8b91da7a52d5b7881a096c52cf59fb07d7a5eefc
ENV PATCHED_COMMIT=f6ae3a23c5c3435eaf7861dc84aa6ca11b409279
ENV FAIL_PASS_TEST_PATHS="test/transformers/test_freeze_core_transformer.py::TestFreezeCoreTransformer::test_full_active_space_1 test/transformers/test_freeze_core_transformer.py::TestFreezeCoreTransformer::test_freeze_core test/transformers/test_freeze_core_transformer.py::TestFreezeCoreTransformer::test_freeze_core_with_remove_orbitals"
ENV PASS_PASS_TEST_PATHS="test/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_minimal_active_space test/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_unpaired_electron_active_space test/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_arbitrary_active_orbitals test/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_active_space_for_q_molecule_v2"
ENV FAIL_PASS_RESOURCE_PATHS="test/transformers/BeH_sto3g.hdf5 test/transformers/BeH_sto3g_reduced.hdf5 test/transformers/LiH_sto3g.hdf5 test/transformers/LiH_sto3g_reduced.hdf5"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
