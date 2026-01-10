"""Report Generator - Generates PDF and HTML evaluation reports."""

from datetime import datetime
from pathlib import Path

import structlog
from jinja2 import Environment, PackageLoader, select_autoescape
from weasyprint import HTML

from rems.config import settings
from rems.schemas import EvaluationSummary, RecommendationSchema

logger = structlog.get_logger()


class ReportGenerator:
    """Generates evaluation reports in PDF and HTML formats."""

    def __init__(self, output_dir: Path | None = None):
        """
        Initialize the report generator.

        Args:
            output_dir: Directory for output files (uses settings default if None)
        """
        self.output_dir = output_dir or settings.reports_dir
        self.env = Environment(
            loader=PackageLoader("rems.reports", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Register custom filters
        self.env.filters["format_percent"] = self._format_percent
        self.env.filters["format_score"] = self._format_score
        self.env.filters["priority_color"] = self._priority_color
        self.env.filters["quality_color"] = self._quality_color

    def generate(
        self,
        summary: EvaluationSummary,
        recommendations: list[RecommendationSchema],
        formats: list[str] | None = None,
    ) -> dict[str, Path]:
        """
        Generate reports in specified formats.

        Args:
            summary: Evaluation summary
            recommendations: List of recommendations
            formats: List of formats to generate ("pdf", "html"). Defaults to both.

        Returns:
            Dictionary mapping format to output file path
        """
        formats = formats or ["pdf", "html"]
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"evaluation_report_{timestamp}"

        # Prepare template context
        context = self._build_context(summary, recommendations)

        output_files: dict[str, Path] = {}

        # Generate HTML
        if "html" in formats:
            html_path = self.output_dir / f"{base_name}.html"
            self._generate_html(context, html_path)
            output_files["html"] = html_path

        # Generate PDF
        if "pdf" in formats:
            pdf_path = self.output_dir / f"{base_name}.pdf"
            self._generate_pdf(context, pdf_path)
            output_files["pdf"] = pdf_path

        logger.info(
            "Reports generated",
            formats=list(output_files.keys()),
            output_dir=str(self.output_dir),
        )

        return output_files

    def _build_context(
        self,
        summary: EvaluationSummary,
        recommendations: list[RecommendationSchema],
    ) -> dict:
        """Build template context from summary and recommendations."""
        return {
            "title": "Rapport d'Évaluation RAG",
            "generated_at": datetime.now(),
            "summary": summary,
            "recommendations": recommendations,
            "metrics": summary.metrics,
            "component_scores": {
                "retrieval": summary.retrieval_score,
                "generation": summary.generation_score,
            },
            # Group recommendations by priority
            "critical_recommendations": [r for r in recommendations if r.priority == "critical"],
            "high_recommendations": [r for r in recommendations if r.priority == "high"],
            "medium_recommendations": [r for r in recommendations if r.priority == "medium"],
            "low_recommendations": [r for r in recommendations if r.priority == "low"],
        }

    def _generate_html(self, context: dict, output_path: Path) -> None:
        """Generate HTML report."""
        template = self.env.get_template("report.html")
        html_content = template.render(**context)

        with output_path.open("w", encoding="utf-8") as f:
            f.write(html_content)

        logger.debug("Generated HTML report", path=str(output_path))

    def _generate_pdf(self, context: dict, output_path: Path) -> None:
        """Generate PDF report from HTML template."""
        template = self.env.get_template("report.html")
        html_content = template.render(**context)

        HTML(string=html_content).write_pdf(output_path)

        logger.debug("Generated PDF report", path=str(output_path))

    @staticmethod
    def _format_percent(value: float | None) -> str:
        """Format a value as percentage."""
        if value is None:
            return "N/A"
        return f"{value * 100:.1f}%"

    @staticmethod
    def _format_score(value: float | None) -> str:
        """Format a score value."""
        if value is None:
            return "N/A"
        return f"{value:.3f}"

    @staticmethod
    def _priority_color(priority: str) -> str:
        """Get color for priority level."""
        colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#28a745",
        }
        return colors.get(priority, "#6c757d")

    @staticmethod
    def _quality_color(quality: str) -> str:
        """Get color for quality level."""
        colors = {
            "excellent": "#28a745",
            "good": "#20c997",
            "acceptable": "#ffc107",
            "poor": "#fd7e14",
            "critical": "#dc3545",
        }
        return colors.get(quality, "#6c757d")
