// National 2024 crop-type map — paddock-species
//
// 1,158,824 polygons over 15,968 9 km tiles of the NLUM crop mask, classified Canola / Cereal /
// Legume or left unclassified with an abstain_reason. Uploaded as 20 table-asset shards by
// upload_polygons_to_gee.py from the de-duplicated national_2024_crops_merged.gpkg. Scored against
// ABS in output/ABS_COMPARISON_NATIONAL_2024_9km.md: the map calls ~1.18x as much land crop as ABS
// says was sown, so read `abstain` and `ndvi_amp` before trusting raw area. 105,627 classified
// polygons also carry abstain = 'no_crop_shape', a failed phenology-shape check recorded as a flag;
// they are shown as classified here (filter on `abstain` to drop them).
//
// Paste this whole file into code.earthengine.google.com and click Run.

// ---------------------------------------------------------------------------------------
// 1. Load and merge the 20 shards
// ---------------------------------------------------------------------------------------
// Field names in these tables: area_ha, compact, abstain, stub, year, poly_idx, ndvi_amp,
// pred, confidence, p_canola, p_cereal, p_legume, n_obs, clear_frac, treed_frac, n_feat.
// 9 km adopted map (2026-09-10). The retired 3 km map is still at .../paddock_species_national_2024_crops.
var FOLDER = 'projects/ee-christopher-bradley/assets/paddock_species_national_2024_9km_crops';
var SHARD_IDS = [
  'p000', 'p001', 'p002', 'p003', 'p004', 'p005', 'p006', 'p007', 'p008', 'p009',
  'p010', 'p011', 'p012', 'p013', 'p014', 'p015', 'p016', 'p017', 'p018', 'p019'
];

var shards = SHARD_IDS.map(function (id) {
  return ee.FeatureCollection(FOLDER + '/' + id);
});
var crops = ee.FeatureCollection(shards).flatten();

// ---------------------------------------------------------------------------------------
// 2. Split by outcome. Field names were shortened to fit the 10-character DBF limit that
//    Earth Engine's table ingestion enforces via a zipped shapefile:
//      abstain_reason -> abstain     compactness -> compact     n_feat_present -> n_feat
//    Shapefile's DBF format has no true NULL for text, so an abstained polygon's `pred`
//    round-trips as an empty string, not a missing property — `notNull('pred')` would
//    silently treat every abstained polygon as classified. An allow-list on the three real
//    class names is correct regardless of how the empty case is represented.
// ---------------------------------------------------------------------------------------
var CLASSES = ['Canola', 'Cereal', 'Legume'];
var classified = crops.filter(ee.Filter.inList('pred', CLASSES));
var abstained = crops.filter(ee.Filter.inList('pred', CLASSES).not());

var canola = classified.filter(ee.Filter.eq('pred', 'Canola'));
var cereal = classified.filter(ee.Filter.eq('pred', 'Cereal'));
var legume = classified.filter(ee.Filter.eq('pred', 'Legume'));

// ---------------------------------------------------------------------------------------
// 3. Colour, matching the crop in the paddock rather than an arbitrary categorical palette:
//    canola is the one that actually looks yellow from the air, cereal reads as
//    gold/straw, legume as green.
// ---------------------------------------------------------------------------------------
var COLOR = {
  canola: 'f7e017',   // bright yellow — canola flower
  cereal: 'b6862c',   // gold/straw — wheat, barley, oats
  legume: '2e7d32',   // green — chickpea, lentil, faba/field bean
  abstained: 'bdbdbd' // grey — not classified; see `abstain`
};

// `.style()` rasterises a FeatureCollection into one Image, which the Code Editor can tile
// at any zoom level in roughly constant time. Calling Map.addLayer directly on a
// million-plus-feature FeatureCollection instead is the thing that hangs the map.
function styled(fc, color) {
  return fc.style({color: color, fillColor: color, width: 0});
}

Map.setCenter(135, -28, 5);
Map.addLayer(styled(abstained, COLOR.abstained), {}, 'Not classified (abstained)', false);
Map.addLayer(styled(legume, COLOR.legume), {}, 'Legume');
Map.addLayer(styled(cereal, COLOR.cereal), {}, 'Cereal');
Map.addLayer(styled(canola, COLOR.canola), {}, 'Canola');

// ---------------------------------------------------------------------------------------
// 4. Optional alternative views, from NATIONAL_2024_RUN.md §5. Off by default — uncomment
//    the ones you want. Each re-filters the SAME polygons, so nothing is re-classified.
// ---------------------------------------------------------------------------------------

// The area-accurate view: raising the crop-presence gate from 0.35 to 0.50 recovers most of
// the Riverina's canola-share error at the cost of 25% of the classified area nationally
// (CONFIDENCE_FILTER.md / NATIONAL_2024_RUN.md §4).
// var gated = classified.filter(ee.Filter.gt('ndvi_amp', 0.5));
// Map.addLayer(styled(gated, 'e53935'), {}, 'ndvi_amp > 0.5 (area-accurate)', false);

// Only what the model committed to with high confidence.
// var highConf = classified.filter(ee.Filter.gt('confidence', 0.7));
// Map.addLayer(styled(highConf, '1e88e5'), {}, 'confidence > 0.7', false);

// The single largest defect in the product: SAM failing to split large tracts (>300 ha cap),
// 37 Mha across only ~48k polygons — see NATIONAL_2024_RUN.md §4 "Coverage".
// var blobs = crops.filter(ee.Filter.eq('abstain', 'unsegmented_blob'));
// Map.addLayer(styled(blobs, 'ff6f00'), {}, 'unsegmented_blob (SAM defect)', false);

// ---------------------------------------------------------------------------------------
// 5. Legend
// ---------------------------------------------------------------------------------------
function legendRow(color, label) {
  var box = ui.Label('', {
    backgroundColor: color, padding: '8px', margin: '0 8px 4px 0'
  });
  var text = ui.Label(label, {margin: '0 0 4px 0'});
  return ui.Panel([box, text], ui.Panel.Layout.Flow('horizontal'));
}

var legend = ui.Panel({style: {position: 'bottom-left', padding: '8px 12px'}});
legend.add(ui.Label('National 2024 crop type', {fontWeight: 'bold', margin: '0 0 6px 0'}));
legend.add(legendRow(COLOR.canola, 'Canola'));
legend.add(legendRow(COLOR.cereal, 'Cereal'));
legend.add(legendRow(COLOR.legume, 'Legume'));
legend.add(legendRow(COLOR.abstained, 'Not classified'));
Map.add(legend);

// ---------------------------------------------------------------------------------------
// 6. Sanity checks — commented out by default. `.size()` over a 1.3M-feature merged
//    collection is a real server-side reduction and can take 10-30s+ to return; run these
//    one at a time via the Console rather than on every script load.
// ---------------------------------------------------------------------------------------
// print('total polygons', crops.size());
// print('classified', classified.size());
// print('canola', canola.size());
// print('cereal', cereal.size());
// print('legume', legume.size());
