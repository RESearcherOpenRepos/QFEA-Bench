ARG BASE_IMAGE=benchmark-base:qiskit_machine_learning_505_569
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_machine_learning_505_569
ENV REPOSITORY=qiskit-community/qiskit-machine-learning
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/505
ENV PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/569
ENV BASE_COMMIT=3a1f680b5ba9c916e4efaa01968c174779618894
ENV PATCHED_COMMIT=12830368e6ad721f12b7b51bf0eca2938533fd43
ENV PR_HEAD_COMMIT=87929e498c6fd10372ff97080af6d5581b8395ce
ENV FAIL_PASS_TEST_PATHS="test/circuit/library/test_qnn_circuit.py::TestQNNCircuit::test_ansatz_setter test/circuit/library/test_qnn_circuit.py::TestQNNCircuit::test_construction_before_build test/circuit/library/test_qnn_circuit.py::TestQNNCircuit::test_construction_fails test/circuit/library/test_qnn_circuit.py::TestQNNCircuit::test_construction_for_input_missmatch test/circuit/library/test_qnn_circuit.py::TestQNNCircuit::test_copy test/circuit/library/test_qnn_circuit.py::TestQNNCircuit::test_feature_map_construction test/circuit/library/test_qnn_circuit.py::TestQNNCircuit::test_feature_map_setter test/circuit/library/test_qnn_circuit.py::TestQNNCircuit::test_num_qubit_construction test/circuit/library/test_qnn_circuit.py::TestQNNCircuit::test_num_qubit_setter"
ENV PASS_PASS_TEST_PATHS="test/circuit/library/test_raw_feature_vector.py::TestRawFeatureVector::test_bind_after_composition test/circuit/library/test_raw_feature_vector.py::TestRawFeatureVector::test_construction test/circuit/library/test_raw_feature_vector.py::TestRawFeatureVector::test_copy test/circuit/library/test_raw_feature_vector.py::TestRawFeatureVector::test_fully_bound test/circuit/library/test_raw_feature_vector.py::TestRawFeatureVector::test_partially_bound test/circuit/library/test_raw_feature_vector.py::TestRawFeatureVector::test_usage_in_vqc"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
