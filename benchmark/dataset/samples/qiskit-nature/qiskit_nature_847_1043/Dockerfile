ARG BASE_IMAGE=benchmark-base:qiskit_nature_847_1043
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_847_1043
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/847
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/1043
ENV BASE_COMMIT=5d8b8877e14c7a282826d2ea28e4b5582960b461
ENV PATCHED_COMMIT=3e11312a18f970ce1a1b170603fc0ef38ae224e5
ENV PR_HEAD_COMMIT=3e11312a18f970ce1a1b170603fc0ef38ae224e5
ENV FAIL_PASS_TEST_PATHS="test/second_q/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_standalone_usage test/second_q/transformers/test_freeze_core_transformer.py::TestFreezeCoreTransformer::test_standalone_usage"
ENV PASS_PASS_TEST_PATHS="test/second_q/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_arbitrary_active_orbitals test/second_q/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_full_active_space_1 test/second_q/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_minimal_active_space test/second_q/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_numpy_integer test/second_q/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_tuple_num_electrons_with_manual_orbitals test/second_q/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_unpaired_electron_active_space test/second_q/transformers/test_freeze_core_transformer.py::TestFreezeCoreTransformer::test_freeze_core test/second_q/transformers/test_freeze_core_transformer.py::TestFreezeCoreTransformer::test_freeze_core_with_remove_orbitals test/second_q/transformers/test_freeze_core_transformer.py::TestFreezeCoreTransformer::test_full_active_space_1 test/second_q/transformers/test_freeze_core_transformer.py::TestFreezeCoreTransformer::test_no_freeze_core"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
