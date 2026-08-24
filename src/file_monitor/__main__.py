import os
import time
from pathlib import Path

from dynatrace_extension import Extension, Status, StatusValue


class FileMonitorExtension(Extension):
    """
    OneAgent Extension 2.0 — monitors files on the host and reports
    size, age, existence, and (optionally) line count as custom metrics.

    Activation config shape (defined in extension.yaml activationSchema):
      endpoints:
        - file_path: /var/log/myapp.log
          count_lines: true
        - file_path: /data/export/output.csv
          count_lines: false
    """

    def initialize(self):
        self.logger.info("FileMonitorExtension starting up")

    def query(self):
        endpoints = self.activation_config.get("endpoints", [])

        if not endpoints:
            self.report_status(Status(StatusValue.EMPTY_PAYLOAD, "No file endpoints configured"))
            return

        for endpoint in endpoints:
            file_path = endpoint.get("file_path", "").strip()
            if not file_path:
                continue

            self._collect(file_path, count_lines=endpoint.get("count_lines", False))

    def _collect(self, file_path: str, count_lines: bool):
        dims = {"file_path": file_path}
        path = Path(file_path)

        if not path.exists():
            self.report_metric("custom.file.exists", 0, dimensions=dims)
            self.report_metric("custom.file.size_bytes", 0, dimensions=dims)
            self.report_metric("custom.file.age_seconds", 0, dimensions=dims)
            self.logger.warning(f"File not found: {file_path}")
            return

        stat = path.stat()

        self.report_metric("custom.file.exists", 1, dimensions=dims)
        self.report_metric("custom.file.size_bytes", stat.st_size, dimensions=dims)
        self.report_metric("custom.file.age_seconds", time.time() - stat.st_mtime, dimensions=dims)

        if count_lines:
            try:
                with open(file_path, "r", errors="ignore") as f:
                    lines = sum(1 for _ in f)
                self.report_metric("custom.file.line_count", lines, dimensions=dims)
            except OSError as exc:
                self.logger.error(f"Cannot read {file_path}: {exc}")

    def status(self):
        return Status(StatusValue.OK)


def main():
    FileMonitorExtension().run()


if __name__ == "__main__":
    main()
