FROM benchmark-base:pennylane_2492_3742

ENV SAMPLE_ID=pennylane_2492_3742
ENV REPOSITORY_URL=https://github.com/PennyLaneAI/pennylane.git
ENV BASE_COMMIT=388ec4a477ad11a9d86a5db3e39f9bab4d64b841
ENV PATCHED_COMMIT=cc280749fbda71556d169d06d2e5387c25dd2b89
ENV FAIL_PASS_TEST_PATHS="tests/kernels/test_kernels.py::TestKernelMatrix::test_simple_kernel[1] tests/kernels/test_kernels.py::TestKernelMatrix::test_simple_kernel[4] tests/kernels/test_kernels.py::TestKernelMatrix::test_square_kernel_single_datapoint tests/kernels/test_kernels.py::TestKernelMatrix::test_laplace_kernel[4]"
ENV PASS_PASS_TEST_PATHS="tests/kernels/test_kernels.py::TestKernelPolarity::test_correct_calls tests/kernels/test_kernels.py::TestKernelPolarity::test_correct_calls_normalized tests/kernels/test_kernels.py::TestKernelTargetAlignment::test_correct_calls tests/kernels/test_kernels.py::TestKernelTargetAlignment::test_correct_calls_normalized"

WORKDIR /benchmark
COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
