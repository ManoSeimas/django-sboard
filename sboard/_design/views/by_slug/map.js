function(doc) {
    if (doc.slug) {
        emit(doc.slug, null);
    }
    else {
        emit(doc._id, null);
    }
}
