function(doc) {
    if (doc.importance && doc.importance >= 5) {
        emit(doc.created, null);
    }
}
