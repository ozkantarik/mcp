#!/usr/bin/env python3
import json
import os
import sys
import logging
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP(
    "PPCCenter MCP Server",
    description="Bridge Amazon Ads performance (Spend, ACoS, Conversions) and SoStocked inventory metrics directly into AI clients."
)

# Setup logging to stderr (logging to stdout corrupts JSON-RPC stdio transport)
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("ppccenter_mcp")

# --- Mock Database State ---
# Preserved in-memory during the running process
STATE = {
    "ads": {
        "summary": {
            "Today": {"spend": 4120.50, "clicks": 2850, "impressions": 95000, "conversions": 342, "sales": 19240.00},
            "Yesterday": {"spend": 3980.00, "clicks": 2710, "impressions": 91000, "conversions": 315, "sales": 18900.00},
            "Last 7 Days": {"spend": 28450.00, "clicks": 19400, "impressions": 650000, "conversions": 2280, "sales": 131800.00},
            "Last 30 Days": {"spend": 124520.10, "clicks": 84500, "impressions": 2850000, "conversions": 9840, "sales": 579240.00}
        },
        "campaigns": [
            {"id": "c1", "name": "PPC-SL-Sponsors-US", "status": "Active", "budget": 500.00, "spend": 8240.00, "sales": 19570.00, "impressions": 180000, "clicks": 5400},
            {"id": "c2", "name": "PPC-HB-Broad-US", "status": "Active", "budget": 300.00, "spend": 4120.00, "sales": 14720.00, "impressions": 95000, "clicks": 2800},
            {"id": "c3", "name": "PPC-Brand-Exact-US", "status": "Active", "budget": 1000.00, "spend": 15200.00, "sales": 95400.00, "impressions": 350000, "clicks": 11200},
            {"id": "c4", "name": "PPC-SleepMask-Auto", "status": "Paused", "budget": 150.00, "spend": 950.00, "sales": 2100.00, "impressions": 25000, "clicks": 710}
        ]
    },
    "inventory": [
        {"sku": "PPC-SL-09", "name": "Super Light Sleep Mask", "fba_qty": 1240, "velocity": 88.5, "lead_time_days": 18, "status": "Critical"},
        {"sku": "PPC-HB-12", "name": "Hydration Balance Serum", "fba_qty": 1148, "velocity": 41.0, "lead_time_days": 24, "status": "Low"},
        {"sku": "PPC-BK-05", "name": "Blackout Sleep Mask", "fba_qty": 4820, "velocity": 65.2, "lead_time_days": 18, "status": "Healthy"}
    ]
}


@mcp.tool()
def get_ads_summary(date_range: str = "Today") -> str:
    """
    Get a summary of Amazon Advertising metrics (spend, sales, ACoS, click-through rate, conversions) for a given date range.
    Supported date ranges: 'Today', 'Yesterday', 'Last 7 Days', 'Last 30 Days'.
    """
    logger.info(f"Invoking get_ads_summary for date_range: {date_range}")
    summary = STATE["ads"]["summary"].get(date_range)
    if not summary:
        return f"Error: Supported date ranges are: {', '.join(STATE['ads']['summary'].keys())}"
    
    acos = (summary["spend"] / summary["sales"] * 100) if summary["sales"] > 0 else 0
    roas = (summary["sales"] / summary["spend"]) if summary["spend"] > 0 else 0
    ctr = (summary["clicks"] / summary["impressions"] * 100) if summary["impressions"] > 0 else 0
    cvr = (summary["conversions"] / summary["clicks"] * 100) if summary["clicks"] > 0 else 0

    return (
        f"### 📊 Amazon Ads Summary ({date_range})\n"
        f"- **Ad Spend:** ${summary['spend']:,.2f}\n"
        f"- **Sales generated:** ${summary['sales']:,.2f}\n"
        f"- **ACoS (Advertising Cost of Sales):** {acos:.2f}%\n"
        f"- **RoAS (Return on Ad Spend):** {roas:.2f}x\n"
        f"- **Impressions:** {summary['impressions']:,}\n"
        f"- **Clicks:** {summary['clicks']:,} (CTR: {ctr:.2f}%)\n"
        f"- **Conversions:** {summary['conversions']:,} (Conv. Rate: {cvr:.2f}%)"
    )


@mcp.tool()
def get_campaigns(status: str = "Active") -> str:
    """
    Retrieve details of Amazon Ads campaigns matching the specified status (e.g., 'Active', 'Paused', 'All').
    """
    logger.info(f"Invoking get_campaigns for status: {status}")
    campaigns = STATE["ads"]["campaigns"]
    filtered = []
    
    for c in campaigns:
        if status.lower() == "all" or c["status"].lower() == status.lower():
            filtered.append(c)

    if not filtered:
        return f"No campaigns found with status: {status}"

    lines = [
        "### 📈 Amazon Ads Campaigns Report",
        "| ID | Campaign Name | Status | Daily Budget | Spend | Sales | Clicks | ACoS |",
        "|---|---|---|---|---|---|---|---|",
    ]
    
    for c in filtered:
        acos = (c["spend"] / c["sales"] * 100) if c["sales"] > 0 else 0
        acos_str = f"{acos:.1f}%" if acos > 0 else "0.0%"
        lines.append(
            f"| {c['id']} | **{c['name']}** | {c['status']} | ${c['budget']:.2f} | ${c['spend']:.2f} | ${c['sales']:.2f} | {c['clicks']:,} | {acos_str} |"
        )
        
    return "\n".join(lines)


@mcp.tool()
def update_campaign_budget(campaign_id: str, new_budget: float) -> str:
    """
    Update the daily budget limit of a specific campaign by its Campaign ID (e.g., 'c1', 'c2').
    """
    logger.info(f"Invoking update_campaign_budget for ID: {campaign_id} to ${new_budget}")
    if new_budget <= 0:
        return "Error: Daily budget must be a positive value."
        
    for c in STATE["ads"]["campaigns"]:
        if c["id"].lower() == campaign_id.lower() or c["name"].lower() == campaign_id.lower():
            old_budget = c["budget"]
            c["budget"] = new_budget
            return f"✅ Success: Campaign **{c['name']}** budget updated from **${old_budget:.2f}/day** to **${new_budget:.2f}/day**."

    return f"Error: Campaign matching ID or Name '{campaign_id}' was not found."


@mcp.tool()
def get_inventory_alerts(days_threshold: int = 30) -> str:
    """
    Retrieve products from SoStocked where the stock days remaining falls below the specified threshold.
    """
    logger.info(f"Invoking get_inventory_alerts with threshold: {days_threshold}")
    alerts = []
    
    for item in STATE["inventory"]:
        days_stock = item["fba_qty"] / item["velocity"] if item["velocity"] > 0 else 999
        if days_stock <= days_threshold:
            alerts.append((item, days_stock))
            
    if not alerts:
        return f"✅ Healthy: No inventory SKU days of stock fall below {days_threshold} days."

    lines = ["### ⚠️ SoStocked Stock Alerts (Threshold: < {} Days)".format(days_threshold)]
    for item, days in alerts:
        status_flag = "🚨 RESTOCK CRITICAL" if days <= item["lead_time_days"] else "⚠️ LOW STOCK"
        lines.append(
            f"- **{item['name']}** (`{item['sku']}`):\n"
            f"  - **FBA Qty:** {item['fba_qty']:,} units (Velocity: {item['velocity']}/day)\n"
            f"  - **Stock Days Remaining:** {days:.1f} days\n"
            f"  - **Supplier Lead Time:** {item['lead_time_days']} days\n"
            f"  - **Status:** **{status_flag}**"
        )
        
    return "\n".join(lines)


@mcp.tool()
def get_reorder_recommendations() -> str:
    """
    Get restful procurement replenishment recommendation table calculated from sales velocity and supplier lead times.
    """
    logger.info("Invoking get_reorder_recommendations")
    lines = [
        "### 📦 Procurement Restocking Plan",
        "| SKU | Item Name | Daily Velocity | Stock Days | Status | Recommended Order Qty |",
        "|---|---|---|---|---|---|",
    ]
    
    for item in STATE["inventory"]:
        days = item["fba_qty"] / item["velocity"] if item["velocity"] > 0 else 999
        
        # Calculate Order Qty (approx 60-day stock buffer)
        reorder_qty = 0
        if days <= 30:
            reorder_qty = int(item["velocity"] * 30 * 2)  # 60 day replenishment
            
        status_str = f"Healthy"
        if days <= item["lead_time_days"]:
            status_str = "🚨 Critical"
        elif days <= 30:
            status_str = "⚠️ Low"
            
        recommend_qty_str = f"**{reorder_qty:,} units**" if reorder_qty > 0 else "0 (Adequate Stock)"
        
        lines.append(
            f"| {item['sku']} | **{item['name']}** | {item['velocity']}/day | {days:.1f} days | {status_str} | {recommend_qty_str} |"
        )
        
    return "\n".join(lines)


if __name__ == "__main__":
    # Standard stdio host entry point
    mcp.run(transport="stdio")
