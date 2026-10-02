ARG BASE_IMAGE=benchmark-base:qiskit_machine_learning_400_436
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_machine_learning_400_436
ENV REPOSITORY=qiskit-community/qiskit-machine-learning
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/400
ENV PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/436
ENV BASE_COMMIT=670bc12ac7b696acdf4b1ea3e9f4242953a8555d
ENV PATCHED_COMMIT=ea94895f607065b2eb24a087c710dfa332debc24
ENV PR_HEAD_COMMIT=024d1361981f427e5fcf6664b2a30db647c1dfdb
ENV FAIL_PASS_TEST_PATHS="test/neural_networks/test_sampler_qnn.py::TestSamplerQNN::test_sampler_qnn_01__True___default___0__2__True_ test/neural_networks/test_sampler_qnn.py::TestSamplerQNN::test_sampler_qnn_04__True___default___1__2__False_ test/neural_networks/test_sampler_qnn.py::TestSamplerQNN::test_sampler_qnn_07__True___shots___0__2__True_ test/neural_networks/test_sampler_qnn.py::TestSamplerQNN::test_sampler_qnn_13__False___default___0__2__True_ test/neural_networks/test_sampler_qnn.py::TestSamplerQNN::test_sampler_qnn_18__False___default___2__2__False_ test/neural_networks/test_sampler_qnn.py::TestSamplerQNN::test_sampler_qnn_gradient_1__True__0__2_ test/neural_networks/test_sampler_qnn.py::TestSamplerQNN::test_sampler_qnn_gradient_4__False__0__2_ test/neural_networks/test_sampler_qnn.py::TestSamplerQNN::test_setters_getters test/neural_networks/test_circuit_vs_sampler_qnn.py::TestCircuitQNNvsSamplerQNN::test_new_vs_old_1__True__True_ test/neural_networks/test_circuit_vs_sampler_qnn.py::TestCircuitQNNvsSamplerQNN::test_new_vs_old_4__False__False_ test/algorithms/classifiers/test_vqc.py::TestVQC::test_VQC_079___sampler___2___zz_feature_map____real_amplitudes___None___binary__ test/algorithms/classifiers/test_vqc.py::TestVQC::test_VQC_non_parameterized_2_sampler test/algorithms/classifiers/test_vqc.py::TestVQC::test_sparse_arrays_6___sampler____cross_entropy__"
ENV PASS_PASS_TEST_PATHS="test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_default_observables test/neural_networks/test_circuit_qnn.py::TestCircuitQNN::test_circuit_qnn_01__True__True___statevector___0__1_ test/neural_networks/test_neural_network.py::TestNeuralNetwork::test_data_gradients test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_untrained test/algorithms/classifiers/test_qsvc.py::TestQSVC::test_qsvc"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
