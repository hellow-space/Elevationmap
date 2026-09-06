// Test adapter only: generated header contains unchanged repository function bodies.
#include <Eigen/Core>
#include <Eigen/Eigenvalues>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>
#include <utility>
#include "original_fit.inc"

int main() {
  int kernel;
  double resolution;
  std::cout << std::setprecision(17);
  while (std::cin >> kernel >> resolution) {
    if (kernel < 1 || resolution <= 0.0) return 2;
    SlidingWindowPlaneExtractor extractor;
    extractor.parameters_.kernel_size = kernel;
    extractor.segmentedPlanesMap_.resolution = resolution;
    Eigen::MatrixXf window(kernel, kernel);
    for (int row = 0; row < kernel; ++row) {
      for (int col = 0; col < kernel; ++col) {
        std::string value;
        if (!(std::cin >> value)) return 2;
        window(row, col) = std::stof(value);
      }
    }
    const auto result = extractor.computeNormalAndErrorForWindow(window);
    std::cout << result.first.x() << ' ' << result.first.y() << ' '
              << result.first.z() << ' ' << result.second << '\n';
  }
}
