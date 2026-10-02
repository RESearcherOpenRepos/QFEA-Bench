FROM benchmark-base:qiskit_nature_129_161

WORKDIR /workspace

ENV SAMPLE_ID=qiskit_nature_129_161
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/129
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/161
ENV BASE_COMMIT=c1de5bd9d0aa07fdf2a4ad83d5c3ae310cff3768
ENV PATCHED_COMMIT=6847323f65a785bc9b0e8a767c91ca6a5d0cdfdf
ENV PR_HEAD_COMMIT=6847323f65a785bc9b0e8a767c91ca6a5d0cdfdf
ENV FAIL_PASS_TEST_PATHS="test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_hermiticity test/operators/second_quantization/test_spin_op.py::TestSpinOp::test_hermiticity test/operators/second_quantization/test_vibrational_op.py::TestVibrationalOp::test_hermiticity"
ENV PASS_PASS_TEST_PATHS="test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_reduce test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_add test/operators/second_quantization/test_spin_op.py::TestSpinOp::test_reduce test/operators/second_quantization/test_spin_op.py::TestSpinOp::test_flatten_ladder_ops test/operators/second_quantization/test_vibrational_op.py::TestVibrationalOp::test_init_pm_label test/operators/second_quantization/test_vibrational_op.py::TestVibrationalOp::test_add"

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
