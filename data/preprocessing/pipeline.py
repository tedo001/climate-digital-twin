"""Composable, reusable processing pipelines.

A :class:`ProcessingPipeline` threads an input value through an ordered list of
named :class:`PipelineStep` callables, logging progress and wrapping any failure
in a :class:`PipelineError` that names the offending step. Steps are plain
callables ``value -> value``, so any function in this package (or a
``functools.partial`` of one) can be dropped into a pipeline unchanged.

:func:`build_raster_pipeline` assembles the canonical raster-conditioning chain
described in SAD Section 6 — clip → reproject → resample → fill gaps →
normalize — from configurable parameters.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Generic, TypeVar

from core.models.region import BoundingBox
from data.preprocessing.clipping import clip_to_bbox
from data.preprocessing.interpolation import interpolate_missing
from data.preprocessing.raster import RasterLayer
from data.preprocessing.reprojection import reproject
from data.preprocessing.resampling import resample
from utils.exceptions import PipelineError
from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

StepFn = Callable[[T], T]


@dataclass(frozen=True, slots=True)
class PipelineStep(Generic[T]):
    """A single named transformation within a pipeline.

    Attributes:
        name: Human-readable step label (used in logs and errors).
        fn: The transformation callable ``value -> value``.
    """

    name: str
    fn: StepFn[T]

    def apply(self, value: T) -> T:
        """Run this step's function on ``value``."""
        return self.fn(value)


class ProcessingPipeline(Generic[T]):
    """An ordered, reusable sequence of processing steps.

    Args:
        steps: The steps to run, in order.
        name: Optional pipeline label for logging.
    """

    def __init__(self, steps: list[PipelineStep[T]], name: str = "pipeline") -> None:
        self._steps = list(steps)
        self._name = name

    @property
    def steps(self) -> tuple[PipelineStep[T], ...]:
        """The configured steps, in execution order."""
        return tuple(self._steps)

    def add(self, name: str, fn: StepFn[T]) -> ProcessingPipeline[T]:
        """Append a step and return ``self`` for fluent chaining.

        Args:
            name: Step label.
            fn: Transformation callable.

        Returns:
            This pipeline, to allow ``pipeline.add(...).add(...)``.
        """
        self._steps.append(PipelineStep(name, fn))
        return self

    def run(self, value: T) -> T:
        """Execute every step in order against ``value``.

        Args:
            value: The initial input.

        Returns:
            The fully-transformed output.

        Raises:
            PipelineError: If any step raises, wrapping the original exception
                and naming the failing step.
        """
        result = value
        for index, step in enumerate(self._steps):
            try:
                result = step.apply(result)
            except Exception as exc:
                raise PipelineError(
                    "Processing pipeline step failed",
                    details={
                        "pipeline": self._name,
                        "step": step.name,
                        "position": index,
                        "error": str(exc),
                    },
                ) from exc
            logger.debug("[%s] step '%s' complete", self._name, step.name)
        return result

    def __len__(self) -> int:
        return len(self._steps)


def build_raster_pipeline(
    *,
    clip_bbox: BoundingBox | None = None,
    dst_crs: str | None = None,
    target_resolution_deg: float | None = None,
    fill_gaps: bool = True,
    normalizer: StepFn[RasterLayer] | None = None,
) -> ProcessingPipeline[RasterLayer]:
    """Build the canonical raster-conditioning pipeline from parameters.

    Only the requested stages are included, so the same builder serves both a
    full clean-and-normalize run and a minimal clip-only run.

    Args:
        clip_bbox: If given, clip to this extent first.
        dst_crs: If given, reproject to this CRS.
        target_resolution_deg: If given, resample to this resolution.
        fill_gaps: Whether to interpolate missing cells.
        normalizer: Optional final normalization step (e.g. a ``partial`` of
            :func:`data.preprocessing.normalization.min_max_normalize` adapted to
            return only the layer).

    Returns:
        A configured :class:`ProcessingPipeline` over :class:`RasterLayer`.
    """
    steps: list[PipelineStep[RasterLayer]] = []
    if clip_bbox is not None:
        steps.append(PipelineStep("clip", partial(clip_to_bbox, bbox=clip_bbox)))
    if dst_crs is not None:
        steps.append(PipelineStep("reproject", partial(reproject, dst_crs=dst_crs)))
    if target_resolution_deg is not None:
        steps.append(
            PipelineStep("resample", partial(resample, target_resolution_deg=target_resolution_deg))
        )
    if fill_gaps:
        steps.append(PipelineStep("fill_missing", interpolate_missing))
    if normalizer is not None:
        steps.append(PipelineStep("normalize", normalizer))
    return ProcessingPipeline(steps, name="raster_conditioning")
