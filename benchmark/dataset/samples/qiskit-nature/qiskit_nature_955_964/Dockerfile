ARG BASE_IMAGE=benchmark-base:qiskit_nature_955_964
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_955_964
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/955
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/964
ENV BASE_COMMIT=abfb7a421b4d7f7d62408811c3ef8d86f02e4403
ENV PATCHED_COMMIT=cd0fcca70df419d19ce975ba047c00a48c527775
ENV PR_HEAD_COMMIT=b1bde972b57cfe428de00bc492acbf7f2969e96c
ENV FAIL_PASS_TEST_PATHS="test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_einsum"
ENV PASS_PASS_TEST_PATHS="test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_add test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_apply test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_compose test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_expand test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_get_item test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_init test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_is_dense test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_is_empty test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_is_sparse test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_iter test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_len test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_1_0_0 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_2_0_75 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_3_1_5 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_4_2_25 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_5_3_0 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_tensor test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_to_dense test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_to_sparse"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
