ARG BASE_IMAGE=benchmark-base:qiskit_nature_337_520
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_337_520
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/337
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/520
ENV BASE_COMMIT=aaa41f7d94c6aaed3c22a4c3709a1e361289ddd9
ENV PATCHED_COMMIT=373fe1d040ee9a00aa1ecb94d487009f7827c0fc
ENV PR_HEAD_COMMIT=373fe1d040ee9a00aa1ecb94d487009f7827c0fc
ENV FAIL_PASS_TEST_PATHS="test/second_q/operators/test_tensor_ordering.py::TestTwoBodySymmetryConversion::test_find_index_order_1 test/second_q/operators/test_tensor_ordering.py::TestTwoBodySymmetryConversion::test_find_index_order_2 test/second_q/operators/test_tensor_ordering.py::TestTwoBodySymmetryConversion::test_find_index_order_3 test/second_q/operators/test_tensor_ordering.py::TestTwoBodySymmetryConversion::test_find_index_order_4 test/second_q/operators/test_tensor_ordering.py::TestTwoBodySymmetryConversion::test_to_chemist_ordering_1 test/second_q/operators/test_tensor_ordering.py::TestTwoBodySymmetryConversion::test_to_chemist_ordering_2 test/second_q/operators/test_tensor_ordering.py::TestTwoBodySymmetryConversion::test_to_chemist_ordering_3 test/second_q/operators/test_tensor_ordering.py::TestTwoBodySymmetryConversion::test_to_physicist_ordering_1 test/second_q/operators/test_tensor_ordering.py::TestTwoBodySymmetryConversion::test_to_physicist_ordering_2 test/second_q/operators/test_tensor_ordering.py::TestTwoBodySymmetryConversion::test_to_physicist_ordering_3 test/second_q/operators/test_tensor_ordering.py::TestTwoBodySymmetryConversion::test_unknown_to_chemist_ordering test/second_q/operators/test_tensor_ordering.py::TestTwoBodySymmetryConversion::test_unknown_to_physicist_ordering"
ENV PASS_PASS_TEST_PATHS="test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_init test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_get_item test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_len test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_iter test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_1_0_0 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_2_0_75 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_3_1_5 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_4_2_25 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_5_3_0 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_add test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_conjugate test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_transpose"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
