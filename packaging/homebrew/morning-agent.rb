# Homebrew formula for Morning Agent.
#
# Destination: the tap repo `rafalgawlik/homebrew-tap`, file `Formula/morning-agent.rb`.
# Then installation is:  brew install rafalgawlik/tap/morning-agent
#
# IMPORTANT: after creating the v1.0.0 release on GitHub, replace `sha256` under `url`
# (see README, "Publishing via Homebrew").
class MorningAgent < Formula
  include Language::Python::Virtualenv

  desc "macOS menu bar app that emails you a morning briefing (OpenRouter + Resend)"
  homepage "https://github.com/rafalgawlik/morning-agent"
  url "https://github.com/rafalgawlik/morning-agent/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "REPLACE_WITH_RELEASE_TARBALL_SHA256"
  license "MIT"

  depends_on :macos
  depends_on "python@3.12"

  resource "rumps" do
    url "https://files.pythonhosted.org/packages/b2/e2/2e6a47951290bd1a2831dcc50aec4b25d104c0cf00e8b7868cbd29cf3bfe/rumps-0.4.0.tar.gz"
    sha256 "17fb33c21b54b1e25db0d71d1d793dc19dc3c0b7d8c79dc6d833d0cffc8b1596"
  end

  resource "requests" do
    url "https://files.pythonhosted.org/packages/ac/c3/e2a2b89f2d3e2179abd6d00ebd70bff6273f37fb3e0cc209f48b39d00cbf/requests-2.34.2.tar.gz"
    sha256 "f288924cae4e29463698d6d60bc6a4da69c89185ad1e0bcc4104f584e960b9ed"
  end

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/a3/c2/24167ea9858356b47a87a50d39908bfdb72ceeefe0041586e704e5376b3a/certifi-2026.7.22.tar.gz"
    sha256 "741e2c3b351ddf169a738da9f2c048608ff7f2c5cc02f1ebc6b118bb090d5d55"
  end

  resource "charset-normalizer" do
    url "https://files.pythonhosted.org/packages/e5/3f/143b048436775b0f76ac3eec145c019e8173ccc2885c8f20319b996d5e83/charset_normalizer-3.5.1.tar.gz"
    sha256 "6117b84ea48435e5356dc737f5121485c30920ba43375fa7b434fd753df0eac3"
  end

  resource "idna" do
    url "https://files.pythonhosted.org/packages/f5/08/8eea9d4b8302028f3abb2c0813953f7aec26d33b7a8960ed760e65ff29fa/idna-3.20.tar.gz"
    sha256 "a7db850025b95ded1eae8a46181a1a6c56c92c96f0e2b005d9ff8dc0210cab44"
  end

  resource "urllib3" do
    url "https://files.pythonhosted.org/packages/e3/05/b17359e1cefb4f909b5e40b1b90a496d987258916dbbf88e842c729f510e/urllib3-2.8.0.tar.gz"
    sha256 "63bf2ead4c879426ebf22ef2a781eeb4aa3b4ae798a0435506f8687fd5bb9b63"
  end

  resource "pyobjc-core" do
    url "https://files.pythonhosted.org/packages/a5/78/abc4ce5920305780aeb36b4067a86253378b36e29ba96673a3deb02eb03a/pyobjc_core-12.2.2.tar.gz"
    sha256 "3906452339cd06a3bb07df103c2511d4cb0f7a22d8771c0b802eba15d9a642b6"
  end

  resource "pyobjc-framework-Cocoa" do
    url "https://files.pythonhosted.org/packages/75/76/49c6da2c6a831020b4854ba20079d5a1030474bffc776b7b73c2eeff8c15/pyobjc_framework_cocoa-12.2.2.tar.gz"
    sha256 "c96c0ef69a71afbbb0e6a7d594b455c5fe47d62e0db376ee7a2b4b828c16ace9"
  end

  resource "pyobjc-framework-WebKit" do
    url "https://files.pythonhosted.org/packages/6f/1f/766e338197f7051c25f23cb0d350caa88234b31c3a759127f2cbb67f3376/pyobjc_framework_webkit-12.2.2.tar.gz"
    sha256 "e5588df2a73b377b59a994cc2a78b467e4341f4e4d28b52e8671e21a2811d3c1"
  end

  def install
    virtualenv_install_with_resources
  end

  # Enables:  brew services start morning-agent
  service do
    run [opt_bin/"morning-agent"]
    keep_alive true
    log_path var/"log/morning-agent.log"
    error_log_path var/"log/morning-agent.log"
  end

  test do
    assert_match "morning-agent #{version}", shell_output("#{bin}/morning-agent --version")
  end
end
