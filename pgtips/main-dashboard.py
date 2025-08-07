from grafana_foundation_sdk.builders.dashboard import Dashboard, Row, ThresholdsConfig
from grafana_foundation_sdk.builders import azuremonitor, timeseries, stat
from grafana_foundation_sdk.cog.encoder import JSONEncoder
from grafana_foundation_sdk.models.common import TimeZoneBrowser
from grafana_foundation_sdk.models import units
from grafana_foundation_sdk.models.dashboard import DataSourceRef, ThresholdsMode, Threshold

def build_azure_query(datasource: DataSourceRef, query) -> azuremonitor.AzureMonitorQuery:
    queryBuilder = (azuremonitor.AzureMonitorQuery()
        .datasource(datasource)
        .ref_id("A")
        .azure_log_analytics(azuremonitor.AzureLogsQuery()
            .query(query)
            .resources([
                "/subscriptions/64865690-933f-4328-9a41-6b2f546777af/resourceGroups/monitor/providers/Microsoft.Insights/components/monitor"
            ])
            .result_format(azuremonitor.azuremonitor.ResultFormat.TIME_SERIES)
        )
        .query_type("Azure Log Analytics")
    )
    return queryBuilder

def build_dashboard() -> Dashboard:
    datasource = DataSourceRef("grafana-azure-monitor-datasource", "fp9e08q4z")
    builder = (
        Dashboard("[TEST] pgTips")
        .uid("estatemanagent-pgtips-main")
        .tags(["generated", "estate-management", "sql-monitor", "pgtips"])
        .refresh("1m")
        .time("now-90d", "now")
        .timezone(TimeZoneBrowser)
        .with_row(
            Row("North Star")
            .collapsed(True)
            .with_panel(
                timeseries.Panel()
                .title("Number of monitored PostgreSQL instances and base monitors with a PostgreSQL instance")
                .min(0)
                .datasource(datasource)
                .with_target(
                    build_azure_query(
                        datasource,
                        '''customEvents
                        | where name == "monitoredentities.report"
                        | where customDimensions["DeveloperMode"] != true
                        | where timestamp < endofday(ago(1d))
                        | summarize arg_max(timestamp, numPostgresInstances=toint(customDimensions["postgresInstances"])) by user_Id, bin(timestamp, 1d)
                        | where numPostgresInstances > 0
                        | summarize
                            total_postgres_instances=sum(numPostgresInstances),
                            base_monitor_count=dcount(user_Id)
                            by bin(timestamp, 1d)
                        '''
                    )
                )
            )
            .with_panel(
                stat.Panel()
                .title("Monitored PostgreSQL Instances")
                .datasource(datasource)
                .with_target(
                    build_azure_query(
                        datasource,
                        '''customEvents
                        | where name == "monitoredentities.report"
                        | where customDimensions["DeveloperMode"] != true
                        | where timestamp < endofday(ago(1d))
                        | summarize arg_max(timestamp, numPostgresInstances=toint(customDimensions["postgresInstances"])) by user_Id, bin(timestamp, 1d)
                        | where numPostgresInstances > 0
                        | summarize
                            sum(numPostgresInstances)
                            by day=bin(timestamp, 1d)
                        | order by day
                        '''
                    )
                )
                .color_mode("value")
                .graph_mode("none")
                .text_mode("value")
                .thresholds(
                    ThresholdsConfig()
                    .mode(ThresholdsMode.ABSOLUTE)
                    .steps(
                        [
                            Threshold(None, "green"),
                            Threshold(80, "red")
                        ]
                    )
                )
            )
        )
    )

    return builder


if __name__ == "__main__":
    dashboard = build_dashboard().build()
    encoder = JSONEncoder(sort_keys=True, indent=2)

    print(encoder.encode(dashboard))