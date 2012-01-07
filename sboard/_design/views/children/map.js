function(doc) {
    if (doc.parents && doc.parents.length > 0) {
        emit(doc.parents[doc.parents.length-1], null);
    }
}
