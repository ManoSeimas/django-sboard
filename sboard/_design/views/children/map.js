function(doc) {
    if (doc.parent) {
        emit(doc.parent, null);
    }
}
