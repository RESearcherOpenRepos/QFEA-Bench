ARG BASE_IMAGE=benchmark-base:qiskit_machine_learning_328_348
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_machine_learning_328_348
ENV REPOSITORY=qiskit-community/qiskit-machine-learning
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/328
ENV PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/348
ENV BASE_COMMIT=2edc1f106c72a41ae2e99b58ee1edb85aa97d8bf
ENV PATCHED_COMMIT=a56158452e32354dfbc1f4835a0b362446af4eba
ENV PR_HEAD_COMMIT=9e1f744fa1f5e7a283c2f2dac9bd9f986ffd24bd
ENV FAIL_PASS_TEST_PATHS="test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_sparse_arrays test/algorithms/classifiers/test_vqc.py::TestVQC::test_sparse_arrays"
ENV PASS_PASS_TEST_PATHS="test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_categorical_data_2__True___squared_error__ test/algorithms/classifiers/test_vqc.py::TestVQC::test_vqc_5__None___statevector__"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
