export const exportToCSV = (data: any[], filenamePrefix: string = 'brand_intelligence_report') => {
    if (!data || data.length === 0) return;

    // Extraer cabeceras de las llaves del primer objeto
    const headers = Object.keys(data[0]);
    const rows = data.map(obj => 
        headers.map(header => obj[header])
    );

    const csvContent = [
        headers.map(h => h.replace(/_/g, ' ').toUpperCase()).join(","),
        ...rows.map(row =>
            row.map(cell => {
                const flatCell = cell === null || cell === undefined ? '' : String(cell);
                return `"${flatCell.replace(/"/g, '""')}"`;
            }).join(",")
        )
    ].join("\n");

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `${filenamePrefix}_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};
