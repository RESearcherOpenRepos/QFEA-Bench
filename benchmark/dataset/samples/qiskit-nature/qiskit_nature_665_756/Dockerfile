ARG BASE_IMAGE=benchmark-base:qiskit_nature_665_756
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_665_756
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/665
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/756
ENV BASE_COMMIT=e286beff0f11efb3288d07a5f77343e4a547c26f
ENV PATCHED_COMMIT=c765c724a0f1e862104ab639ae27c963da86ae44
ENV PR_HEAD_COMMIT=c765c724a0f1e862104ab639ae27c963da86ae44
ENV FAIL_PASS_TEST_PATHS="test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_add test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_conjugate test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_get_item test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_init test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_iter test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_len test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_1_0_0 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_2_0_75 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_3_1_5 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_4_2_25 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_mul_5_3_0 test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_transpose"
ENV PASS_PASS_TEST_PATHS="test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_mul test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_add test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_adjoint test/second_q/operators/test_spin_op.py::TestSpinOp::test_mul test/second_q/operators/test_spin_op.py::TestSpinOp::test_add test/second_q/operators/test_spin_op.py::TestSpinOp::test_adjoint test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_mul test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_add test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_hermiticity"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
