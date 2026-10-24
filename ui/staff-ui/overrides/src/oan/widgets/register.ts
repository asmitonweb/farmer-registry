import { createElement } from 'react';
import { HeaderSectionWidget, widgetRegistry } from '@openg2p/registry-widgets';
import { EnumeratorPositionWidget } from './EnumeratorPositionWidget';
import { EthiopicDateWidget } from './EthiopicDateWidget';
import { FARMER_PHOTO_VARIANT, FarmerPhotoWidget } from './FarmerPhotoWidget';
import { GeoPointWidget } from './GeoPointWidget';

// The widget package uploads a section's photo, and sets the field named by
// the widget's "image" path (record_image_document_id), only for widgets of
// type "header-section" (sectionFiles.ts). The farmer photo keeps that type in
// the section metadata so its upload takes that route, and is told apart by
// "widget-variant". Every other header-section is upstream's widget, unchanged.
type Props = { config: Record<string, unknown> } & Record<string, unknown>;

function HeaderSectionOrVariant(props: Props) {
    if (props.config['widget-variant'] === FARMER_PHOTO_VARIANT) {
        return createElement(FarmerPhotoWidget, props);
    }
    return createElement(HeaderSectionWidget, props as never);
}

widgetRegistry.register({ widget: 'header-section', component: HeaderSectionOrVariant });

// OAN's own widget types. A widget with an object "widget-data-path" saves
// every field it names (sectionSnapshot.ts), so each of these saves its pair
// or set of fields with the section.
widgetRegistry.register({ widget: 'oan-ethiopic-date', component: EthiopicDateWidget as never });
widgetRegistry.register({ widget: 'oan-geo-point', component: GeoPointWidget as never });
widgetRegistry.register({ widget: 'oan-enumerator-position', component: EnumeratorPositionWidget as never });
