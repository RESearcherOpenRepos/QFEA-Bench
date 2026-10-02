ARG BASE_IMAGE=benchmark-base:qiskit_machine_learning_960_1021
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_machine_learning_960_1021
ENV REPOSITORY=qiskit-community/qiskit-machine-learning
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/960
ENV PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/1021
ENV BASE_COMMIT=46d9ba4b4c7e946f1ee14fd75455fd05909e4271
ENV PATCHED_COMMIT=ef567f6e12906d7a4c7f3e6dbafb8ec546f98749
ENV PR_HEAD_COMMIT=efbf1595a448e5ccd6ba029c9b8e53818ba6f83a
ENV FAIL_PASS_TEST_PATHS="test/utils/loss_functions/test_regression_kernel_loss.py::TestRegressionKernelLoss::test_regression_loss_fit_1_SVRLoss test/utils/loss_functions/test_regression_kernel_loss.py::TestRegressionKernelLoss::test_regression_loss_fit_2_MSRLoss test/utils/loss_functions/test_regression_kernel_loss.py::TestRegressionKernelLoss::test_regression_loss_fit_3_MARLoss test/utils/loss_functions/test_regression_kernel_loss.py::TestRegressionKernelLoss::test_regression_loss_fit_4_HuberLoss"
ENV PASS_PASS_TEST_PATHS="test/utils/loss_functions/test_loss_functions.py::TestLossFunctions::test_cross_entropy_loss_1 test/utils/loss_functions/test_loss_functions.py::TestLossFunctions::test_cross_entropy_loss_2"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
