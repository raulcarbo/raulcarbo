/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import {
    Component,
    onWillStart,
    onMounted,
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

function isoDate(d) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export class CarbotecniaDashboard extends Component {
    static template = "carbotecnia_dashboard.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            period: "month", // month | quarter | year
            loading: true,
            kpis: {
                total: 0,
                delta: null, // % vs periodo anterior
                orders: 0,
                avgTicket: 0,
                newLeads: 0,
                pipeline: 0,
            },
        });
        this.trendRef = useRef("trendChart");
        this.sellerRef = useRef("sellerChart");
        this.categRef = useRef("categChart");
        this.clientsRef = useRef("clientsChart");
        this.charts = [];
        this.data = null;

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            this.data = await this.loadData();
            this.state.loading = false;
        });
        onMounted(() => this.renderCharts());
        onWillUnmount(() => this.destroyCharts());
    }

    // ------------------------------------------------------------------
    // Periodos
    // ------------------------------------------------------------------
    getRange() {
        const now = new Date();
        let start, end, prevStart, prevEnd;
        if (this.state.period === "month") {
            start = new Date(now.getFullYear(), now.getMonth(), 1);
            end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
            prevStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            prevEnd = new Date(now.getFullYear(), now.getMonth(), 0);
        } else if (this.state.period === "quarter") {
            const q = Math.floor(now.getMonth() / 3);
            start = new Date(now.getFullYear(), q * 3, 1);
            end = new Date(now.getFullYear(), q * 3 + 3, 0);
            prevStart = new Date(now.getFullYear(), q * 3 - 3, 1);
            prevEnd = new Date(now.getFullYear(), q * 3, 0);
        } else {
            start = new Date(now.getFullYear(), 0, 1);
            end = new Date(now.getFullYear(), 11, 31);
            prevStart = new Date(now.getFullYear() - 1, 0, 1);
            prevEnd = new Date(now.getFullYear() - 1, 11, 31);
        }
        return { start, end, prevStart, prevEnd };
    }

    async setPeriod(p) {
        if (this.state.period === p) {
            return;
        }
        this.state.period = p;
        this.state.loading = true;
        this.data = await this.loadData();
        this.state.loading = false;
        this.renderCharts();
    }

    // ------------------------------------------------------------------
    // Datos (sale.report + crm.lead, vía ORM — respeta permisos)
    // ------------------------------------------------------------------
    saleDomain(start, end) {
        return [
            ["state", "not in", ["draft", "sent", "cancel"]],
            ["date", ">=", isoDate(start)],
            ["date", "<=", isoDate(end) + " 23:59:59"],
        ];
    }

    async loadData() {
        const { start, end, prevStart, prevEnd } = this.getRange();
        const domain = this.saleDomain(start, end);
        const now = new Date();
        const trendStart = new Date(now.getFullYear(), now.getMonth() - 11, 1);

        const [
            totalGroups,
            prevGroups,
            bySeller,
            byCateg,
            byClient,
            trendGroups,
            orders,
            newLeads,
            pipeGroups,
        ] = await Promise.all([
            this.orm.readGroup("sale.report", domain, ["price_total:sum"], []),
            this.orm.readGroup(
                "sale.report",
                this.saleDomain(prevStart, prevEnd),
                ["price_total:sum"],
                []
            ),
            this.orm.readGroup(
                "sale.report",
                domain,
                ["price_total:sum"],
                ["user_id"],
                { orderby: "price_total desc" }
            ),
            this.orm.readGroup(
                "sale.report",
                domain,
                ["price_total:sum"],
                ["categ_id"],
                { orderby: "price_total desc" }
            ),
            this.orm.readGroup(
                "sale.report",
                domain,
                ["price_total:sum"],
                ["partner_id"],
                { orderby: "price_total desc", limit: 8 }
            ),
            this.orm.readGroup(
                "sale.report",
                this.saleDomain(trendStart, now),
                ["price_total:sum"],
                ["date:month"]
            ),
            this.orm.searchCount("sale.order", [
                ["state", "=", "sale"],
                ["date_order", ">=", isoDate(start)],
                ["date_order", "<=", isoDate(end) + " 23:59:59"],
            ]),
            this.orm.searchCount("crm.lead", [
                ["create_date", ">=", isoDate(start)],
                ["create_date", "<=", isoDate(end) + " 23:59:59"],
            ]),
            this.orm.readGroup(
                "crm.lead",
                [["type", "=", "opportunity"], ["active", "=", true]],
                ["expected_revenue:sum"],
                []
            ),
        ]);

        const total = totalGroups[0]?.price_total || 0;
        const prevTotal = prevGroups[0]?.price_total || 0;
        this.state.kpis = {
            total,
            delta: prevTotal ? ((total - prevTotal) / prevTotal) * 100 : null,
            orders,
            avgTicket: orders ? total / orders : 0,
            newLeads,
            pipeline: pipeGroups[0]?.expected_revenue || 0,
        };

        const label = (g, key) => (g[key] ? g[key][1] : "Sin asignar");
        return {
            sellers: bySeller.map((g) => ({ name: label(g, "user_id"), value: g.price_total || 0 })),
            categs: byCateg.map((g) => ({ name: label(g, "categ_id"), value: g.price_total || 0 })),
            clients: byClient.map((g) => ({ name: label(g, "partner_id"), value: g.price_total || 0 })),
            trend: trendGroups.map((g) => ({ name: g["date:month"], value: g.price_total || 0 })),
        };
    }

    // ------------------------------------------------------------------
    // Gráficas (Chart.js, incluido en Odoo — bundle web.chartjs_lib)
    // ------------------------------------------------------------------
    destroyCharts() {
        this.charts.forEach((c) => c.destroy());
        this.charts = [];
    }

    makeChart(ref, config) {
        if (!ref.el) {
            return;
        }
        const chart = new Chart(ref.el.getContext("2d"), config);
        this.charts.push(chart);
    }

    renderCharts() {
        this.destroyCharts();
        const d = this.data;
        if (!d) {
            return;
        }
        const moneyTick = (v) => new Intl.NumberFormat("es-MX", { notation: "compact" }).format(v);
        const tooltipMoney = {
            callbacks: { label: (ctx) => ` ${fmtMXN(ctx.parsed.y ?? ctx.parsed.x ?? ctx.parsed)}` },
        };

        this.makeChart(this.trendRef, {
            type: "line",
            data: {
                labels: d.trend.map((r) => r.name),
                datasets: [{
                    label: "Ventas",
                    data: d.trend.map((r) => r.value),
                    borderColor: PALETTE[0],
                    backgroundColor: PALETTE[0] + "22",
                    fill: true,
                    tension: 0.3,
                }],
            },
            options: {
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: tooltipMoney },
                scales: { y: { ticks: { callback: moneyTick } } },
            },
        });

        this.makeChart(this.sellerRef, {
            type: "bar",
            data: {
                labels: d.sellers.map((r) => r.name),
                datasets: [{
                    data: d.sellers.map((r) => r.value),
                    backgroundColor: d.sellers.map((_, i) => PALETTE[i % PALETTE.length]),
                }],
            },
            options: {
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: tooltipMoney },
                scales: { y: { ticks: { callback: moneyTick } } },
            },
        });

        this.makeChart(this.categRef, {
            type: "doughnut",
            data: {
                labels: d.categs.map((r) => r.name),
                datasets: [{
                    data: d.categs.map((r) => r.value),
                    backgroundColor: d.categs.map((_, i) => PALETTE[i % PALETTE.length]),
                }],
            },
            options: {
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right" },
                    tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${fmtMXN(ctx.parsed)}` } },
                },
            },
        });

        this.makeChart(this.clientsRef, {
            type: "bar",
            data: {
                labels: d.clients.map((r) => r.name),
                datasets: [{
                    data: d.clients.map((r) => r.value),
                    backgroundColor: PALETTE[1],
                }],
            },
            options: {
                indexAxis: "y",
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: tooltipMoney },
                scales: { x: { ticks: { callback: moneyTick } } },
            },
        });
    }

    // ------------------------------------------------------------------
    // Helpers de template
    // ------------------------------------------------------------------
    fmtMXN(v) {
        return fmtMXN(v);
    }

    get deltaText() {
        const d = this.state.kpis.delta;
        if (d === null) {
            return "—";
        }
        return `${d >= 0 ? "▲" : "▼"} ${Math.abs(d).toFixed(1)}% vs periodo anterior`;
    }
}

registry.category("actions").add("carbotecnia_dashboard", CarbotecniaDashboard);
