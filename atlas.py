from PyQt5 import QtGui
from PyQt5.QtCore import QVariant

region_name_field = "NAZEV"
city_name_field = "NAZOB_ENG"
population_count_field = "OB01"
workspace = "C:\\PGIS\\QGIS_atlas"
city_regions = "obce.shp"
city_points = "obce_b.shp"
roads = "silnice.shp"
rivers = "vod_tok.shp"
regions = "okresy.shp"

# load city shapefile as layer
obce_lyr = QgsVectorLayer(workspace + "\\" + city_regions, "cities", "ogr")

# load ORP shapefile as layer
regions_lyr = QgsVectorLayer(workspace + "\\" + regions, "okresy", "ogr")


#add population density field to polygon city layer
layer_provider = obce_lyr.dataProvider()
layer_provider.addAttributes([QgsField("Density", QVariant.Double)])
obce_lyr.updateFields()

# calculate population density and update field
features = obce_lyr.getFeatures()
for f in features:
    area = f.geometry().area()/10**6
    new_value = f[population_count_field]/area
    with edit(obce_lyr):
        f["Density"] = new_value
        obce_lyr.updateFeature(f)


# create map fature layers
roads = QgsVectorLayer(workspace + "\\" + roads, "roads", "ogr")
rivers = QgsVectorLayer(workspace + "\\" + rivers, "rivers", "ogr")
cities_points = QgsVectorLayer(workspace + "\\" + city_points, "cities_points", "ogr")

# for each region (okres)
for i in range(1, regions_lyr.featureCount() - 1):
    #in my data region number 57 has wrong geometry
    #if i == 57:
        #continue
        
    # select region and create its temporary layer
    regions_lyr.select(i)
    output_path1 = workspace + "\\temp_region" + str(i) + ".shp"
    writer = QgsVectorFileWriter.writeAsVectorFormat(regions_lyr, output_path1, "UTF-8", regions_lyr.crs(), "ESRI Shapefile", onlySelected = True)
    region = QgsVectorLayer(output_path1, "region", "ogr")
    
    # remove current selection
    regions_lyr.removeSelection()
    
    # get name of the region
    row = region.getFeature(0)
    title_text = row[region_name_field]
    
    # create temporary layer from city counties
    output_path2 = workspace + "\\temp_counties" + str(i) + ".shp"
    counties_clipped = processing.run("native:clip", {'INPUT' : obce_lyr, 'OUTPUT' : output_path2, 'OVERLAY' : region})
    counties = QgsVectorLayer(output_path2, "kartogram", "ogr")
    
    # calculate attribute extremes
    min_value = counties.minimumValue(counties.fields().indexFromName("Density"))
    max_value = counties.maximumValue(counties.fields().indexFromName("Density"))
    
    # compute interval breaks
    breaks = QgsGraduatedSymbolRenderer().calcEqualIntervalBreaks(min_value, max_value, 5, False, 0, False)
    breaks.insert(0, min_value)
    for k in range(len(breaks)):
        breaks[k] = round(breaks[k], 1)
    
    # list of colors for each interval
    colors = ["#ffcccc", "#ff9999", "#ff6666", "#ff3333", "#ff0000"]
    
    # list of interval ranges
    range_list = []
    
    # fill range_list with QgsRendererRange objects
    for j in range(5):
        minVal = breaks[j]
        maxVal = breaks[j+1]
        symbol1 = QgsSymbol.defaultSymbol(counties.geometryType())
        symbol1.setColor(QtGui.QColor(colors[j]))
        symbol1.setOpacity(1)
        lab = str(minVal) + " - " + str(maxVal)
        range1 = QgsRendererRange(minVal, maxVal, symbol1, lab)
        range_list.append(range1)
        
    # create the renderer
    groupRenderer = QgsGraduatedSymbolRenderer('', range_list)
    groupRenderer.setMode(QgsGraduatedSymbolRenderer.EqualInterval)
    groupRenderer.setClassAttribute("Density")

    # apply renderer to layer
    counties.setRenderer(groupRenderer)
    
    # add to QGIS interface
    QgsProject.instance().addMapLayer(counties)
    
    # create road layer
    roads_clipped = processing.run("native:clip", {'INPUT' : roads, 'OUTPUT' : 'TEMPORARY_OUTPUT', 'OVERLAY' : region})
    roads_clipped["OUTPUT"].setName('silnice')
    symbol = QgsLineSymbol.createSimple({'color': 'black', "width": 0.38})
    roads_clipped["OUTPUT"].renderer().setSymbol(symbol)
    QgsProject.instance().addMapLayer(roads_clipped["OUTPUT"])
    
    # create river layer
    rivers_clipped = processing.run("native:clip", {'INPUT' : rivers, 'OUTPUT' : 'TEMPORARY_OUTPUT', 'OVERLAY' : region})
    rivers_clipped["OUTPUT"].setName('vodní toky')
    symbol = QgsLineSymbol.createSimple({'color': '#3790f8', "width": 0.36})
    rivers_clipped["OUTPUT"].renderer().setSymbol(symbol)
    QgsProject.instance().addMapLayer(rivers_clipped["OUTPUT"])
    
    #create city point layer
    cities_clipped = processing.run("native:clip", {'INPUT' : cities_points, 'OUTPUT' : 'TEMPORARY_OUTPUT', 'OVERLAY' : region})
    cities_clipped["OUTPUT"].setName('města')
    symbol = QgsSymbol.defaultSymbol(cities_clipped["OUTPUT"].geometryType())
    symbol.setColor(QtGui.QColor("black"))
    cities_clipped["OUTPUT"].renderer().setSymbol(symbol)
    
    # add label settings
    settings = QgsPalLayerSettings()
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Arial", 9))
    text_format.setSize(9)
    
    # add buffer settings to labels
    buffer_settings = QgsTextBufferSettings()
    buffer_settings.setEnabled(True)
    buffer_settings.setSize(0.7)
    buffer_settings.setColor(QColor("white"))
    text_format.setBuffer(buffer_settings)
    settings.setFormat(text_format)
    settings.fieldName = city_name_field
    settings.placement = 2
    settings.enabled = True
    
    # upadate labels
    layer_settings = QgsVectorLayerSimpleLabeling(settings)
    cities_clipped["OUTPUT"].setLabelsEnabled(True)
    cities_clipped["OUTPUT"].setLabeling(layer_settings)
    QgsProject.instance().addMapLayer(cities_clipped["OUTPUT"])
    
    # initialize layout
    project = QgsProject.instance()
    manager = project.layoutManager()
    layoutName = "Layout1"
    
    # delete layouts with same name
    layouts_list = manager.printLayouts()
    for layout in layouts_list:
        if layout.name() == layoutName:
            manager.removeLayout(layout)
    
    # create layout
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(layoutName)
    
    # set layout size to A4 and orientation to "portrait"
    pc = layout.pageCollection()
    pc.pages()[0].setPageSize('A4', QgsLayoutItemPage.Orientation.Portrait)
    
    manager.addLayout(layout)
    
    # create map object
    map = QgsLayoutItemMap(layout)
    map.setRect(20,20,20,20)
    
    # define layers to be in layout
    ms = QgsMapSettings()
    ms.setLayers([counties, roads_clipped["OUTPUT"], rivers_clipped["OUTPUT"], cities_clipped["OUTPUT"]])
    
    # create boudaries of maps' full extent
    rect = QgsRectangle(ms.fullExtent())
    ms.setExtent(rect)
    map.setExtent(rect)
    
    # set background color to white
    map.setBackgroundColor(QColor(255,255,255,0))
    
    # add map object to layout
    layout.addLayoutItem(map)
    
    # move and resize map frame in the layout
    map.attemptMove(QgsLayoutPoint(10, 40, QgsUnitTypes.LayoutMillimeters))
    map.attemptResize(QgsLayoutSize(190, 180, QgsUnitTypes.LayoutMillimeters))
    
    # create legend of the graduated symbol layer
    legend = QgsLayoutItemLegend(layout)
    legend.setTitle("obyv./km^2")
    layerTree = QgsLayerTree()
    layerTree.addLayer(counties)
    legend.model().setRootGroup(layerTree)
    layout.addLayoutItem(legend)
    legend.attemptMove(QgsLayoutPoint(140, 230, QgsUnitTypes.LayoutMillimeters))
    
    # create legend of the rest of layers
    checked_layers = [layer.name() for layer in QgsProject().instance().layerTreeRoot().children() if layer.isVisible() and layer.name() != "kartogram"]
    layersToAdd = [layer for layer in QgsProject().instance().mapLayers().values() if layer.name() in checked_layers]
    root = QgsLayerTree()
    for layer in layersToAdd:
        #add layer ob   jects to the layer tree
        root.addLayer(layer)
    legend2 = QgsLayoutItemLegend(layout)
    legend2.model().setRootGroup(root)
    layout.addLayoutItem(legend2)
    legend2.attemptMove(QgsLayoutPoint(90, 230, QgsUnitTypes.LayoutMillimeters))
    
    # create scalebar
    scalebar = QgsLayoutItemScaleBar(layout)
    scalebar.setStyle("Line Ticks Up")
    scalebar.setUnits(QgsUnitTypes.DistanceKilometers)
    scalebar.setNumberOfSegments(2)
    scalebar.setNumberOfSegmentsLeft(0)
    scalebar.setUnitsPerSegment(2.5)
    scalebar.setLinkedMap(map)
    scalebar.setUnitLabel("km")
    scalebar.setFont(QFont("Arial", 9))
    scalebar.update()
    layout.addLayoutItem(scalebar)
    scalebar.attemptMove(QgsLayoutPoint(20, 230, QgsUnitTypes.LayoutMillimeters))
    
    # create title
    title = QgsLayoutItemLabel(layout)
    title.setText(title_text)
    title.setFont(QFont("Arial", 24))
    title.adjustSizeToText()
    layout.addLayoutItem(title)
    title.attemptMove(QgsLayoutPoint(70, 20, QgsUnitTypes.LayoutMillimeters))
    
    #export layout
    layout = manager.layoutByName(layoutName)
    exporter = QgsLayoutExporter(layout)
    fn = workspace + "\\atlas" + str(i) + ".pdf"
    exporter.exportToPdf(fn, QgsLayoutExporter.PdfExportSettings())
    
    #delete all active layers
    layer_group = QgsProject.instance()
    layer_group.removeMapLayer(layer_group.mapLayersByName("kartogram")[0].id())
    layer_group.removeMapLayer(layer_group.mapLayersByName("silnice")[0].id())
    layer_group.removeMapLayer(layer_group.mapLayersByName("vodní toky")[0].id())
    layer_group.removeMapLayer(layer_group.mapLayersByName("města")[0].id())