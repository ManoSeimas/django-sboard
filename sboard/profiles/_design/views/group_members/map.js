function(doc) {
    if (doc.doc_type == 'MembershipNode' && doc.group && doc.profile) {
        // Membership
        emit([doc.group, doc.term_from, doc._id, 1], null);
        // Profile
        emit([doc.group, doc.term_from, doc._id, 2], {_id: doc.profile});
    }
}
