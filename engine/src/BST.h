#ifndef VIRUS_DEFENSE_BST_H
#define VIRUS_DEFENSE_BST_H

struct BSTNode {
    int degree;
    int node_id;
    BSTNode* left;
    BSTNode* right;
};

class BST {
private:
    BSTNode* root;

    BSTNode* insertRec(BSTNode* node, int node_id, int degree);
    BSTNode* removeRec(BSTNode* node, int node_id, int degree);
    BSTNode* findMin(BSTNode* node);
    void destroy(BSTNode* node);
    int compare(int node_id_a, int degree_a, int node_id_b, int degree_b) const;
    void findMaxRec(BSTNode* node, int& best_id, int& best_degree) const;

public:
    BST();
    ~BST();

    void clear();
    void insert(int node_id, int degree);
    void remove(int node_id, int degree);
    void update(int node_id, int old_deg, int new_deg);
    int findMax() const;
};

#endif
