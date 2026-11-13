"""Matplotlib rendering helpers for PulsarLab.

This module receives already-computed ``ModelResult`` objects. It never parses
files, mutates projects, or recalculates the scientific model.
"""

from __future__ import annotations

import numpy as np
from matplotlib import ticker

from pulsarlab.datasets.dataset import PulsarProject
from pulsarlab.engine.pipeline import ModelResult
from pulsarlab.visualization import theme as T


def _txt(labels: dict[str, str] | None, key: str, fallback: str) -> str:
    return fallback if labels is None else labels.get(key, fallback)


def style_axis_text(ax) -> None:
    """Colour *every* tick label (major **and** minor) and the offset text.

    ``Axes.tick_params`` only touches major ticks unless ``which='both'`` is
    given.  On a logarithmic axis whose range does not span a whole decade the
    *only* labels Matplotlib draws are minor ones, which therefore came out in
    Matplotlib's default black on the dark panel and looked as if the axis had
    no numbers.  Call this again after ``set_xscale``/``set_yscale``.
    """
    ax.tick_params(axis="both", which="both", colors=T.MUTED, labelcolor=T.MUTED)
    ax.yaxis.get_offset_text().set_color(T.MUTED)
    ax.xaxis.get_offset_text().set_color(T.MUTED)


def apply_dark_theme(fig, axes) -> None:
    fig.patch.set_facecolor(T.BG)
    for ax in np.ravel(np.array(axes, dtype=object)):
        ax.set_facecolor(T.BG_PANEL)
        style_axis_text(ax)
        ax.xaxis.label.set_color(T.TEXT)
        ax.yaxis.label.set_color(T.TEXT)
        ax.title.set_color(T.TEXT)
        for spine in ax.spines.values():
            spine.set_color(T.GRID)
        ax.grid(True, color=T.GRID, alpha=0.5, linewidth=0.7)


def use_adaptive_layout(fig, pad: float = 0.08) -> None:
    """Size margins from the real text extents instead of hard-coded fractions.

    Fixed ``subplots_adjust`` fractions assume one font/DPI/canvas height.  On a
    shorter canvas (small laptop window, macOS font metrics, Retina scaling) they
    clipped the title, the ``MJD`` label and tick numbers.  The constrained
    layout engine re-solves the margins on every draw, including window resizes.
    """
    fig.set_layout_engine("constrained")
    engine = fig.get_layout_engine()
    if engine is not None:
        engine.set(w_pad=pad, h_pad=pad)


def _short_label(text: str, limit: int = 28) -> str:
    """Middle-ellipsis for long project names used as tick labels."""
    text = str(text)
    if len(text) <= limit:
        return text
    head = max(1, (limit - 1) // 2)
    tail = max(1, limit - 1 - head)
    return text[:head] + "…" + text[-tail:]


def _errorbar(ax, x, y, yerr, *, color, label, visibility, ms: float = 3.0, alpha: float = 0.86):
    """Data points with 1σ error bars (bars omitted if toggled off or all NaN)."""
    kwargs = {"fmt": ".", "ms": ms, "alpha": alpha, "color": color, "label": label, "zorder": 3}
    if bool(visibility.get("errorbars", True)) and yerr is not None:
        yerr = np.asarray(yerr, dtype=float)
        if yerr.size and np.any(np.isfinite(yerr)):
            kwargs.update(yerr=yerr, elinewidth=0.9, capsize=3.0, capthick=0.9)
    return ax.errorbar(np.asarray(x, dtype=float), np.asarray(y, dtype=float), **kwargs)


def _set_legend(ax) -> None:
    handles, _labels = ax.get_legend_handles_labels()
    if not handles:
        return
    leg = ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8, frameon=True)
    if leg is None:
        return
    leg.get_frame().set_facecolor(T.BG_PANEL)
    leg.get_frame().set_edgecolor(T.GRID)
    for text in leg.get_texts():
        text.set_color(T.TEXT)


def _artist_set_visible(artist, visible: bool) -> None:
    if hasattr(artist, "set_visible"):
        artist.set_visible(bool(visible))
    for child in getattr(artist, "lines", []) or []:
        if isinstance(child, tuple):
            for sub in child:
                if hasattr(sub, "set_visible"):
                    sub.set_visible(bool(visible))
        elif hasattr(child, "set_visible"):
            child.set_visible(bool(visible))


def _glitch_visible(visibility: dict[str, bool]) -> bool:
    return bool(visibility.get("glitches", True))


def _break_at_epochs(x: np.ndarray, y: np.ndarray, epochs: list[float], gap_days: float = 2e-8) -> tuple[np.ndarray, np.ndarray]:
    """Insert NaNs around discontinuities so renderers do not draw fake ramps."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size == 0 or y.size == 0 or not epochs:
        return x, y
    order = np.argsort(x)
    x = x[order]
    y = y[order]
    out_x: list[float] = []
    out_y: list[float] = []
    epoch_values = [float(e) for e in epochs if e is not None and np.isfinite(float(e))]
    for i, (xx, yy) in enumerate(zip(x, y)):
        if i > 0:
            prev = x[i - 1]
            for epoch in epoch_values:
                if ((prev < epoch <= xx) or (prev <= epoch < xx)) and abs(xx - prev) > gap_days:
                    out_x.append(np.nan)
                    out_y.append(np.nan)
                    break
        out_x.append(float(xx))
        out_y.append(float(yy))
    return np.asarray(out_x), np.asarray(out_y)


def _glitch_epochs(result: ModelResult) -> list[float]:
    return [float(g["glep"]) for g in result.glitch_groups if g.get("glep") is not None]


def _computed_projects(projects: list[PulsarProject], results: dict[str, ModelResult]) -> list[PulsarProject]:
    return [project for project in projects if project.dataset_id in results]


def _empty_axis(ax, message: str, keep_x: bool = False) -> None:
    """Show a centred message instead of data.

    ``keep_x`` must be True when the x axis is shared with other panels:
    ``set_xticks([])`` on a shared axis removes the numbers from *all* of them.
    """
    ax.text(0.5, 0.5, message, ha="center", va="center", color=T.TEXT, transform=ax.transAxes)
    if not keep_x:
        ax.set_xticks([])
    ax.set_yticks([])
    ax.yaxis.set_minor_locator(ticker.NullLocator())


def _display_indices(size: int, limit: int = 25000) -> np.ndarray:
    """Return deterministic indices for plotting without changing analysis data.

    Large TIM/DAT files remain fully loaded and fully analyzed. Only Matplotlib
    rendering is thinned because drawing hundreds of thousands of individual
    artists can block the Qt event loop for several seconds.
    """
    n = max(0, int(size))
    cap = max(2, int(limit))
    if n <= cap:
        return np.arange(n, dtype=int)
    return np.linspace(0, n - 1, cap, dtype=int)


def draw_glitch_rail(ax, project: PulsarProject, result: ModelResult, y: float = 1.010, show_labels: bool = True) -> None:
    trans = ax.get_xaxis_transform()
    for group in result.glitch_groups:
        glep = group.get("glep")
        if glep is None:
            continue
        label = group.get("label", "G")
        ax.axvline(float(glep), color=T.GLITCH, alpha=0.42, linewidth=1.0, linestyle=":", zorder=1)
        if not show_labels:
            continue
        ax.text(
            float(glep), y, label,
            transform=trans,
            ha="center", va="bottom", fontsize=8,
            color=T.GLITCH,
            bbox={"boxstyle": "round,pad=0.18", "facecolor": T.BG, "edgecolor": T.GLITCH, "alpha": 0.95, "linewidth": 0.8},
            clip_on=False,
            zorder=20,
        )


def _draw_f0_axis(
    ax,
    projects: list[PulsarProject],
    results: dict[str, ModelResult],
    visibility: dict[str, bool],
    labels: dict[str, str] | None = None,
) -> dict[str, object]:
    artists: dict[str, object] = {}
    for idx, project in enumerate(_computed_projects(projects, results), start=1):
        result = results[project.dataset_id]
        color = T.DATASET_COLORS[(idx - 1) % len(T.DATASET_COLORS)]
        epochs = _glitch_epochs(result)
        obs = project.observations

        if obs is not None:
            obs_label = f"D{idx} F0 obs"
            display_label = f"D{idx} F0 {_txt(labels, 'legend.observed', 'observed')}"
            shown = _display_indices(obs.n)
            artists[obs_label] = _errorbar(
                ax, np.asarray(obs.mjd)[shown], np.asarray(obs.f0)[shown],
                np.asarray(obs.f0_err)[shown], color=color, label=display_label,
                visibility=visibility,
            )
        model_label = f"D{idx} F0 model"
        baseline_label = f"D{idx} F0 no glitches"
        x, y = _break_at_epochs(result.model_mjd, result.f0_model, epochs)
        model_display = f"D{idx} F0 {_txt(labels, 'legend.model', 'model')}"
        baseline_display = f"D{idx} F0 {_txt(labels, 'legend.no_glitches', 'no glitches')}"
        artists[model_label], = ax.plot(x, y, color=T.MODEL if idx == 1 else color, linewidth=1.55, alpha=0.90, label=model_display)
        artists[baseline_label], = ax.plot(result.model_mjd, result.f0_noglit, color=T.MUTED, linewidth=1.0, alpha=0.70, linestyle=":", label=baseline_display)
        if _glitch_visible(visibility):
            draw_glitch_rail(ax, project, result)

    for key, artist in artists.items():
        _artist_set_visible(artist, bool(visibility.get(key, True)))
    return artists


def _draw_f1_axis(
    ax,
    projects: list[PulsarProject],
    results: dict[str, ModelResult],
    visibility: dict[str, bool],
    labels: dict[str, str] | None = None,
) -> dict[str, object]:
    artists: dict[str, object] = {}
    for idx, project in enumerate(_computed_projects(projects, results), start=1):
        result = results[project.dataset_id]
        color = T.DATASET_COLORS[(idx - 1) % len(T.DATASET_COLORS)]
        epochs = _glitch_epochs(result)
        obs = project.observations

        if obs is not None and obs.f1 is not None:
            f1_label = f"D{idx} F1 obs"
            shown = _display_indices(obs.n)
            f1_err = None if obs.f1_err is None else np.asarray(obs.f1_err)[shown] * 1e15
            display_label = f"D{idx} F1 {_txt(labels, 'legend.observed', 'observed')}"
            artists[f1_label] = _errorbar(
                ax, np.asarray(obs.mjd)[shown], np.asarray(obs.f1)[shown] * 1e15,
                f1_err, color=color, label=display_label, alpha=0.78, visibility=visibility,
            )
        model_label = f"D{idx} F1 model"
        baseline_label = f"D{idx} F1 no glitches"
        x1, y1 = _break_at_epochs(result.model_mjd, result.f1_model * 1e15, epochs)
        model_display = f"D{idx} F1 {_txt(labels, 'legend.model', 'model')}"
        baseline_display = f"D{idx} F1 {_txt(labels, 'legend.no_glitches', 'no glitches')}"
        artists[model_label], = ax.plot(x1, y1, color=T.F1 if idx == 1 else color, linewidth=1.35, alpha=0.90, label=model_display)
        artists[baseline_label], = ax.plot(result.model_mjd, result.f1_noglit * 1e15, color=T.MUTED, linewidth=1.0, alpha=0.65, linestyle=":", label=baseline_display)
        if _glitch_visible(visibility):
            draw_glitch_rail(ax, project, result)

    for key, artist in artists.items():
        _artist_set_visible(artist, bool(visibility.get(key, True)))
    return artists


def _draw_spin_axes(
    axes,
    projects: list[PulsarProject],
    results: dict[str, ModelResult],
    visibility: dict[str, bool],
    labels: dict[str, str] | None = None,
) -> dict[str, object]:
    ax0, ax1 = axes
    artists = _draw_f0_axis(ax0, projects, results, visibility, labels)
    artists.update(_draw_f1_axis(ax1, projects, results, visibility, labels))
    return artists


def plot_spin(
    fig,
    datasets: list[PulsarProject],
    results: dict[str, ModelResult],
    visibility: dict[str, bool] | None = None,
    labels: dict[str, str] | None = None,
) -> dict[str, object]:
    """Backward-compatible two-panel spin plot."""
    visibility = visibility or {}
    fig.clear()
    axes = fig.subplots(2, 1, sharex=True)
    apply_dark_theme(fig, axes)
    artists = _draw_spin_axes(axes, datasets, results, visibility, labels)
    axes[0].set_title(_txt(labels, "spin.title", "Spin evolution"), pad=30)
    axes[0].set_ylabel("F0 [Hz]")
    axes[1].set_ylabel("F1 [10^-15 Hz/s]")
    axes[1].set_xlabel("MJD")
    for ax in axes:
        _set_legend(ax)
    use_adaptive_layout(fig)
    return artists


def plot_phase(fig, datasets: list[PulsarProject], results: dict[str, ModelResult], labels: dict[str, str] | None = None) -> None:
    """Backward-compatible phase view retained for the Python API."""
    fig.clear()
    axes = fig.subplots(3, 1, sharex=True)
    apply_dark_theme(fig, axes)
    computed = _computed_projects(datasets, results)
    if not computed:
        _empty_axis(axes[0], _txt(labels, "phase.load_par", "Load a PAR file to compute phase."))
    for idx, project in enumerate(computed, start=1):
        result = results[project.dataset_id]
        color = T.DATASET_COLORS[(idx - 1) % len(T.DATASET_COLORS)]
        axes[0].plot(result.model_mjd, result.phase, color=color, label=f"D{idx} {_txt(labels, 'legend.phase', 'phase')}")
        axes[1].plot(result.model_mjd, result.phase_dot, color=color, label=f"D{idx} dφ/dt")
        axes[2].plot(result.model_mjd, result.phase_ddot, color=color, label=f"D{idx} d²φ/dt²")
    axes[0].set_title(_txt(labels, "phase.title", "Phase evolution"))
    axes[0].set_ylabel(_txt(labels, "phase.ylabel", "Phase [cycles]"))
    axes[1].set_ylabel("F0 [Hz]")
    axes[2].set_ylabel("F1 [Hz s⁻¹]")
    axes[2].set_xlabel("MJD")
    for ax in axes:
        _set_legend(ax)
    use_adaptive_layout(fig)


def plot_spin_analysis(
    fig,
    projects: list[PulsarProject],
    results: dict[str, ModelResult],
    visibility: dict[str, bool] | None = None,
    labels: dict[str, str] | None = None,
    panels: dict[str, bool] | None = None,
) -> dict[str, object]:
    """Configurable spin view with independently switchable graph panels.

    ``panels`` accepts ``f0``, ``f1``, ``phase``, ``delta_f0`` and
    ``delta_f1``. All panels remain enabled by default for API compatibility;
    the desktop UI starts with only F0 and F1 visible to avoid redundant visual
    density and lets the user activate the diagnostic panels on demand.
    """
    visibility = visibility or {}
    panel_order = ("f0", "f1", "phase", "delta_f0", "delta_f1")
    requested = {key: True for key in panel_order} if panels is None else panels
    enabled = [key for key in panel_order if bool(requested.get(key, False))]
    if not enabled:
        enabled = ["f0"]

    fig.clear()
    raw_axes = fig.subplots(len(enabled), 1, sharex=True)
    axes = np.atleast_1d(raw_axes).ravel()
    apply_dark_theme(fig, axes)
    axis_for = dict(zip(enabled, axes))
    artists: dict[str, object] = {}

    if "f0" in axis_for:
        artists.update(_draw_f0_axis(axis_for["f0"], projects, results, visibility, labels))
    if "f1" in axis_for:
        artists.update(_draw_f1_axis(axis_for["f1"], projects, results, visibility, labels))

    computed = _computed_projects(projects, results)
    for idx, project in enumerate(computed, start=1):
        result = results[project.dataset_id]
        color = T.DATASET_COLORS[(idx - 1) % len(T.DATASET_COLORS)]
        epochs = _glitch_epochs(result)

        if "phase" in axis_for:
            axis_for["phase"].plot(result.model_mjd, result.phase, color=color, linewidth=1.25, label=f"D{idx} {_txt(labels, 'legend.phase', 'phase')}")
        obs = project.observations
        observed = _txt(labels, "legend.observed", "observed")
        if "delta_f0" in axis_for:
            ax = axis_for["delta_f0"]
            xf0, yf0 = _break_at_epochs(result.model_mjd, result.glitch_f0, epochs)
            artists[f"D{idx} ΔF0 model"], = ax.plot(
                xf0, yf0, color=color, linewidth=1.35,
                label=f"D{idx} ΔF0 {_txt(labels, 'legend.glitch', 'glitch')}",
            )
            # DAT counterpart of the curve above: observed F0 minus the
            # no-glitch timing solution, with the DAT F0 uncertainty.
            if obs is not None and result.delta_f0_obs.size == obs.n:
                shown = _display_indices(obs.n)
                artists[f"D{idx} ΔF0 obs"] = _errorbar(
                    ax, np.asarray(obs.mjd)[shown], result.delta_f0_obs[shown],
                    np.asarray(obs.f0_err)[shown], color=color,
                    label=f"D{idx} ΔF0 {observed}", visibility=visibility,
                )
        if "delta_f1" in axis_for:
            ax = axis_for["delta_f1"]
            xf1, yf1 = _break_at_epochs(result.model_mjd, result.glitch_f1 * 1e15, epochs)
            artists[f"D{idx} ΔF1 model"], = ax.plot(
                xf1, yf1, color=color, linewidth=1.35,
                label=f"D{idx} ΔF1 {_txt(labels, 'legend.glitch', 'glitch')}",
            )
            if obs is not None and result.delta_f1_obs is not None and result.delta_f1_obs.size == obs.n:
                shown = _display_indices(obs.n)
                f1_err = None if obs.f1_err is None else np.asarray(obs.f1_err)[shown] * 1e15
                artists[f"D{idx} ΔF1 obs"] = _errorbar(
                    ax, np.asarray(obs.mjd)[shown], result.delta_f1_obs[shown] * 1e15,
                    f1_err, color=color, label=f"D{idx} ΔF1 {observed}", alpha=0.78,
                    visibility=visibility,
                )

        if _glitch_visible(visibility):
            for key in ("phase", "delta_f0", "delta_f1"):
                if key in axis_for:
                    draw_glitch_rail(axis_for[key], project, result)

    if "delta_f0" in axis_for:
        axis_for["delta_f0"].axhline(0, color=T.GRID, linewidth=1)
    if "delta_f1" in axis_for:
        axis_for["delta_f1"].axhline(0, color=T.GRID, linewidth=1)

    # Honour the per-line toggles for the Δ panels (same checkboxes as F0/F1).
    for key, artist in artists.items():
        if "Δ" in key:
            _artist_set_visible(artist, bool(visibility.get(key, True)))

    ylabels = {
        "f0": "F0 [Hz]",
        "f1": "F1 [10^-15 Hz/s]",
        "phase": _txt(labels, "phase.ylabel", "Phase [cycles]"),
        "delta_f0": "ΔF0 [Hz]",
        "delta_f1": "ΔF1 [10^-15 Hz/s]",
    }
    for key, ax in axis_for.items():
        ax.set_ylabel(ylabels[key])
        _set_legend(ax)
    axes[0].set_title(_txt(labels, "spin_analysis.title", "Spin Analysis"), pad=30)
    axes[-1].set_xlabel("MJD")

    use_adaptive_layout(fig)
    return artists


def plot_glitches(fig, datasets: list[PulsarProject], results: dict[str, ModelResult], labels: dict[str, str] | None = None) -> list[dict]:
    """Backward-compatible glitch catalogue."""
    fig.clear()
    ax = fig.subplots(1, 1)
    apply_dark_theme(fig, [ax])
    picked: list[dict] = []
    computed = _computed_projects(datasets, results)
    for idx, project in enumerate(computed, start=1):
        result = results[project.dataset_id]
        y = idx
        span = project.mjd_span
        ax.hlines(y, *span, color=T.GRID, linewidth=1)
        for group in result.glitch_groups:
            glep = group.get("glep")
            if glep is None:
                continue
            marker = ax.scatter([glep], [y], color=T.GLITCH, s=75, zorder=10, picker=True)
            marker._pulsarlab_glitch_group = group
            marker._pulsarlab_dataset_id = project.dataset_id
            ax.annotate(group["label"], xy=(glep, y), xytext=(0, 7), textcoords="offset points", ha="center", va="bottom", color=T.GLITCH, fontsize=8)
            picked.append({"artist": marker, "dataset": project, "group": group})
    ax.set_title(_txt(labels, "glitches.title", "Glitch catalogue"))
    ax.set_xlabel("MJD")
    ax.set_yticks(range(1, len(computed) + 1))
    ax.set_yticklabels([_short_label(f"D{i}: {d.name}") for i, d in enumerate(computed, start=1)], color=T.TEXT)
    if computed:
        ax.set_ylim(0.65, len(computed) + 0.35)
    use_adaptive_layout(fig)
    return picked


def plot_glitches_toas(
    fig,
    projects: list[PulsarProject],
    results: dict[str, ModelResult],
    labels: dict[str, str] | None = None,
    toa_window: float | None = None,
) -> list[dict]:
    """Timeline of glitches, TOA density, and TOA uncertainty.

    Upper panel: one row per project. Each glitch is a green marker; when
    ``toa_window`` is given, the translucent band around it is the ±window
    search interval and the TOAs inside it are drawn bolder (both appear in the
    legend). Lower panel: TOA uncertainty (log scale).
    """
    fig.clear()
    axes = fig.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [1.1, 1.5]})
    apply_dark_theme(fig, axes)
    timeline, errors = axes
    picked: list[dict] = []
    visible_rows = 0
    uncertainty_plotted = False
    window_in_legend = False
    for idx, project in enumerate(projects, start=1):
        color = T.DATASET_COLORS[(idx - 1) % len(T.DATASET_COLORS)]
        y = idx
        visible_rows += 1
        span = project.mjd_span
        if np.all(np.isfinite(span)):
            timeline.hlines(y, *span, color=T.GRID, linewidth=1)
        emphasised_in_legend = False
        if project.toas is not None:
            mjd = np.asarray(project.toas.mjd, dtype=float)
            sigma = np.asarray(project.toas.uncertainty_us, dtype=float)
            shown = _display_indices(project.toas.n)
            timeline.scatter(
                mjd[shown], np.full(shown.size, y, dtype=float), marker="|", s=110,
                linewidths=0.9, color=color, alpha=0.35, label=f"D{idx} TOAs",
            )
            good_idx = np.flatnonzero(np.isfinite(sigma) & (sigma > 0))
            if good_idx.size:
                uncertainty_plotted = True
                good_shown = good_idx[_display_indices(good_idx.size)]
                errors.scatter(mjd[good_shown], sigma[good_shown], s=10, color=color, alpha=0.75, label=f"D{idx} σTOA")
        result = results.get(project.dataset_id)
        if result is not None:
            for group in result.glitch_groups:
                glep = group.get("glep")
                if glep is None:
                    continue
                if toa_window is not None and project.toas is not None:
                    window_label = "_nolegend_"
                    if not window_in_legend:
                        window_in_legend = True
                        window_label = _txt(labels, "glitches_toas.window_legend", "TOA window ±{window:g} d").format(window=float(toa_window))
                    timeline.axvspan(
                        float(glep) - float(toa_window), float(glep) + float(toa_window),
                        color=T.GLITCH, alpha=0.10, zorder=0, label=window_label,
                    )
                    near = project.toas.near_mjd(float(glep), float(toa_window))
                    if near.size:
                        near_shown = near[_display_indices(near.size, limit=5000)]
                        in_window_label = "_nolegend_"
                        if not emphasised_in_legend:
                            emphasised_in_legend = True
                            in_window_label = f"D{idx} " + _txt(labels, "glitches_toas.toas_in_window", "TOAs in window")
                        timeline.scatter(
                            project.toas.mjd[near_shown], np.full(near_shown.size, y, dtype=float),
                            marker="|", s=150, linewidths=1.4, color=color, alpha=1.0, zorder=5,
                            label=in_window_label,
                        )
                marker = timeline.scatter([glep], [y], color=T.GLITCH, edgecolors=T.TEXT, linewidths=0.5, s=78, zorder=15, picker=True)
                marker._pulsarlab_glitch_group = group
                marker._pulsarlab_dataset_id = project.dataset_id
                timeline.annotate(group.get("label", "G"), xy=(glep, y), xytext=(0, 8), textcoords="offset points", ha="center", color=T.GLITCH, fontsize=8)
                errors.axvline(float(glep), color=T.GLITCH, alpha=0.32, linewidth=0.9, linestyle=":")
                picked.append({"artist": marker, "dataset": project, "group": group})

    timeline.set_title(_txt(labels, "glitches_toas.title", "Glitches & TOAs"))
    timeline.set_ylabel(_txt(labels, "glitches_toas.timeline", "Projects"))
    timeline.set_yticks(range(1, visible_rows + 1))
    timeline.set_yticklabels([_short_label(f"D{i}: {p.name}") for i, p in enumerate(projects, start=1)], color=T.TEXT)
    if visible_rows:
        timeline.set_ylim(0.45, visible_rows + 0.65)
    errors.set_ylabel(_txt(labels, "glitches_toas.error", "TOA uncertainty [µs]"))
    errors.set_xlabel("MJD")
    if uncertainty_plotted:
        errors.set_yscale("log")
        # Plain numbers (50, 60, 70 …) instead of 5×10¹ mathtext, and re-apply the
        # tick colours because the scale change creates fresh minor ticks.
        log_fmt = ticker.LogFormatter(base=10.0, labelOnlyBase=False, minor_thresholds=(2.0, 0.6))
        errors.yaxis.set_major_formatter(log_fmt)
        errors.yaxis.set_minor_formatter(log_fmt)
        style_axis_text(errors)
    elif any(project.toas is not None for project in projects):
        _empty_axis(errors, _txt(labels, "glitches_toas.no_uncertainties", "No positive finite TOA uncertainties are available."), keep_x=True)
    else:
        _empty_axis(errors, _txt(labels, "glitches_toas.no_toas", "No TIM/TOA data loaded."), keep_x=True)
    _set_legend(timeline)
    _set_legend(errors)
    use_adaptive_layout(fig)
    return picked


def plot_glitch_contribution(fig, datasets: list[PulsarProject], results: dict[str, ModelResult], labels: dict[str, str] | None = None) -> None:
    """Legacy three-panel contribution API retained for external callers."""
    fig.clear()
    axes = fig.subplots(3, 1, sharex=True)
    apply_dark_theme(fig, axes)
    for idx, project in enumerate(_computed_projects(datasets, results), start=1):
        result = results[project.dataset_id]
        color = T.DATASET_COLORS[(idx - 1) % len(T.DATASET_COLORS)]
        epochs = _glitch_epochs(result)
        xf0, yf0 = _break_at_epochs(result.model_mjd, result.glitch_f0, epochs)
        xf1, yf1 = _break_at_epochs(result.model_mjd, result.glitch_f1 * 1e15, epochs)
        xph, yph = _break_at_epochs(result.model_mjd, result.glitch_phase, epochs)
        axes[0].plot(xf0, yf0, color=color, linewidth=1.5, label=f"D{idx} ΔF0 glitch")
        axes[1].plot(xf1, yf1, color=color, linewidth=1.5, label=f"D{idx} ΔF1 glitch")
        axes[2].plot(xph, yph, color=color, linewidth=1.5, label=f"D{idx} Δphase glitch")
        for ax in axes:
            draw_glitch_rail(ax, project, result)
    for ax in axes:
        ax.axhline(0, color=T.GRID, linewidth=1)
    axes[0].set_title(_txt(labels, "contribution.title", "Glitch contribution"), pad=30)
    axes[0].set_ylabel("ΔF0 [Hz]")
    axes[1].set_ylabel("ΔF1 [10^-15 Hz/s]")
    axes[2].set_ylabel("Δphase [cycles]")
    axes[2].set_xlabel("MJD")
    for ax in axes:
        _set_legend(ax)
    use_adaptive_layout(fig)


def plot_residuals(
    fig,
    datasets: list[PulsarProject],
    results: dict[str, ModelResult],
    labels: dict[str, str] | None = None,
    visibility: dict[str, bool] | None = None,
) -> None:
    """Processed-frequency residuals ``observed - model`` with DAT 1σ error bars.

    The model includes the glitch terms; nothing else is subtracted. The error
    bars are the F0 (F1) uncertainties stored in the DAT file; PAR parameter
    uncertainties are not propagated.

    Bars are drawn for every dataset.  When a dataset's DAT uncertainty is orders
    of magnitude below the residual scatter on the (shared) y axis its bars are
    genuinely sub-pixel at full range; they are never inflated, since they must
    equal the DAT σ.  The UI summary reports σ/RMS so this is not mistaken for
    missing bars.
    """
    visibility = visibility or {}
    fig.clear()
    axes = fig.subplots(2, 1, sharex=True)
    apply_dark_theme(fig, axes)
    plotted = False
    plotted_f1 = False

    for idx, project in enumerate(_computed_projects(datasets, results), start=1):
        if project.observations is None:
            continue
        plotted = True
        result = results[project.dataset_id]
        obs = project.observations
        color = T.DATASET_COLORS[(idx - 1) % len(T.DATASET_COLORS)]
        residual_word = _txt(labels, "legend.residual", "residual")
        axes[0].axhline(0, color=T.GRID, linewidth=1)
        shown = _display_indices(obs.n)
        mjd = np.asarray(obs.mjd)[shown]
        _errorbar(
            axes[0], mjd, np.asarray(result.residual_f0)[shown], np.asarray(obs.f0_err)[shown],
            color=color, label=f"D{idx} F0 {residual_word}", visibility=visibility,
        )
        if result.residual_f1 is not None:
            plotted_f1 = True
            axes[1].axhline(0, color=T.GRID, linewidth=1)
            f1_err = None if obs.f1_err is None else np.asarray(obs.f1_err)[shown] * 1e15
            _errorbar(
                axes[1], mjd, np.asarray(result.residual_f1)[shown] * 1e15, f1_err,
                color=color, label=f"D{idx} F1 {residual_word}", visibility=visibility,
            )
    if not plotted:
        # Nothing at all to plot, so hiding the (shared) x numbers is correct here.
        _empty_axis(axes[0], _txt(labels, "residuals.no_dat", "Load PAR + DAT to compute frequency residuals."))
    elif not plotted_f1:
        _empty_axis(axes[1], _txt(labels, "residuals.no_f1", "The DAT file has no F1 column."), keep_x=True)
    axes[0].set_title(_txt(labels, "residuals.title", "Residuals (observed − model)"))
    # These are *not* the ΔF0/ΔF1 glitch-contribution panels of Spin Analysis, so
    # they get their own names instead of reusing "ΔF0 [Hz]".
    axes[0].set_ylabel(_txt(labels, "residuals.f0_ylabel", "F0 residual [Hz]"))
    axes[1].set_ylabel(_txt(labels, "residuals.f1_ylabel", "F1 residual [10^-15 Hz/s]"))
    axes[1].set_xlabel("MJD")
    for ax in axes:
        _set_legend(ax)
    use_adaptive_layout(fig)


def plot_dataset_summary(
    fig,
    datasets: list[PulsarProject],
    results: dict[str, ModelResult],
    labels: dict[str, str] | None = None,
    visibility: dict[str, bool] | None = None,
) -> None:
    visibility = visibility or {}
    fig.clear()
    ax = fig.subplots(1, 1)
    apply_dark_theme(fig, [ax])
    for idx, project in enumerate(datasets, start=1):
        color = T.DATASET_COLORS[(idx - 1) % len(T.DATASET_COLORS)]
        if project.observations is not None:
            obs = project.observations
            shown = _display_indices(obs.n)
            _errorbar(
                ax, np.asarray(obs.mjd)[shown], np.asarray(obs.f0)[shown], np.asarray(obs.f0_err)[shown],
                color=color, label=f"D{idx} DAT: {project.name}", visibility=visibility, alpha=0.88,
            )
        elif project.dataset_id in results:
            result = results[project.dataset_id]
            ax.plot(result.model_mjd, result.f0_model, linewidth=1.2, color=color, alpha=0.88, label=f"D{idx} PAR: {project.name}")
        if project.toas is not None:
            # TOAs have no F0 ordinate; display a compact rug at the lower axis edge.
            trans = ax.get_xaxis_transform()
            shown = _display_indices(project.toas.n)
            ax.plot(
                np.asarray(project.toas.mjd)[shown], np.full(shown.size, 0.02 + idx * 0.012),
                "|", color=color, alpha=0.60, transform=trans, label=f"D{idx} TIM TOAs",
            )
    ax.set_title(_txt(labels, "datasets.title", "Project summary"))
    ax.set_xlabel("MJD")
    ax.set_ylabel("F0 [Hz]")
    _set_legend(ax)
    use_adaptive_layout(fig)
