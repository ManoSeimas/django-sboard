function(doc) {
    if (doc.title) {
        emit(doc._id, null);
    }
}
