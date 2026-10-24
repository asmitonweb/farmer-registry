import { createElement } from 'react';
import { HeaderSectionWidget, widgetRegistry } from '@openg2p/registry-widgets';
import { FARMER_PHOTO_VARIANT, FarmerPhotoWidget } from './FarmerPhotoWidget';

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
