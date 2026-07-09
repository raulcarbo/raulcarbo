/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import {
    Component,
    onWillStart,
    onMounted,
    onPatched,
    onWillUnmount,
    useState,
    useRef,
} from "@odoo/owl";

const PALETTE = [
    "#1f6f8b", "#e07b39", "#5c9e6f", "#9b5de5", "#d64550",
    "#3a86ff", "#ffb703", "#588157", "#bc6c25", "#6c757d",
];

function fmtMXN(value) {
    return new Intl.NumberFormat("es-MX", {
        style: "currency",
        currency: "MXN",
        maximumFractionDigits: 0,
    }).format(value || 0);
}

function fmtNum(value) {
    return new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 }).format(value || 0);
}

export class CarboDashboardBuilder extends Component {
    static template = "carbotecnia_dashboard.Builder";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.rootRef = useRef("root");
        this.state = useState({ loading: true, dashboards: [], active: null });
        this.charts = [];
        this.needsRender = false;

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.load();
        });
        onMounted(() => this.renderCharts());
        onPatched(() => {
            if (this.needsRender) {
                this.needsRender = false;
                this.renderCharts();
            }
        });
        onWillUnmount(() => this.destroyCharts());
    }

    async load(dashboardId = null) {
        this.state.loading = true;
        const payload = await this.orm.call("carbo.dashboard", "get_builder_data", [dashboardId]);
        this.state.dashboards = payload.dashboards;
        this.state.active = payload.active || null;
        this.state.loading = false;
        this.needsRender = true;
    }

    async onSelectDashboard(ev) {
        await this.load(parseInt(ev.target.value, 10));
    }

    async refresh() {
        await this.load(this.state.active ? this.state.active.id : null);
    }

    openConfig() {
        this.action.doAction("carbotecnia_dashboard.action_carbo_dashboard_config");
    }

    fmtValue(widget, value) {
        return widget.is_money ? fmtMXN(value) : fmtNum(value);
    }

    isNumber(value) {
        return typeof value === "number";
    }

    destroyCharts() {
        this.charts.forEach((chart) => chart.destroy());
        this.charts = [];
    }

    renderCharts() {
        this.destroyCharts();
        const root = this.rootRef.el;
        if (!root || !this.state.active) {
            return;
        }
        for (const widget of this.state.active.widgets) {
            if (widget.display_type !== "chart" || widget.error) {
                continue;
            }
            const canvas = root.querySelector(`canvas[data-wid="${widget.id}"]`);
            if (!canvas) {
                continue;
            }
            const horizontal = widget.chart_type === "hbar";
            const type = horizontal ? "bar" : widget.chart_type;
            const pieLike = type === "pie" || type === "doughnut";
            const fmt = widget.is_money ? fmtMXN : fmtNum;
            const compact = (v) =>
                new Intl.NumberFormat("es-MX", { notation: "compact" }).format(v);

            const config = {
                type,
                data: {
                    labels: widget.labels,
                    datasets: [{
                        label: widget.name,
                        data: widget.values,
                        backgroundColor:
                            type === "line"
                                ? PALETTE[0] + "22"
                                : widget.values.map((_, i) => PALETTE[i % PALETTE.length]),
                        borderColor: type === "line" ? PALETTE[0] : undefined,
                        fill: type === "line",
                        tension: 0.3,
                    }],
                },
                options: {
                    maintainAspectRatio: false,
                    indexAxis: horizontal ? "y" : "x",
                    plugins: {
                        legend: { display: pieLike, position: "right" },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => {
                                    const value = pieLike
                                        ? ctx.parsed
                                        : horizontal
                                          ? ctx.parsed.x
                                          : ctx.parsed.y;
                                    return ` ${ctx.label}: ${fmt(value)}`;
                                },
                            },
                        },
                    },
                    scales: pieLike
                        ? {}
                        : { [horizontal ? "x" : "y"]: { ticks: { callback: compact } } },
                },
            };
            this.charts.push(new Chart(canvas.getContext("2d"), config));
        }
    }
}

registry.category("actions").add("carbo_dashboard_builder", CarboDashboardBuilder);
